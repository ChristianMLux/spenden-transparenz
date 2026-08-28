"""prompt.py, client.py, and the extract_statements job.

The LLM is stubbed at the pipeline.extract.client.extract boundary in every test here - the real
API is never called from a test. Job tests run against the real Postgres schema (job_sessionmaker /
session fixtures from conftest.py), because the gating contract - cost cap, attempt cap, cache,
idempotent rewrite - only exists once rows are actually persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest
from core.models import Disaster, District, IngestionRun, Report, ResponseStatement, StatementDistrict
from sqlalchemy import func, select

import pipeline.extract.client as llm_client
from pipeline.extract.client import ExtractionResult, cost_usd
from pipeline.extract.prompt import PROMPT_VERSION, STATEMENT_TOOL, ReportInput, build_messages
from pipeline.jobs.extract import MAX_ATTEMPTS, extract_statements

# --- prompt.build_messages -----------------------------------------------------------------------


def test_build_messages_returns_a_system_and_a_user_message():
    report = ReportInput(url="https://example.org/r", title="Flood report", body="IFRC responded.")
    messages = build_messages(report)
    assert [m["role"] for m in messages] == ["system", "user"]


def test_system_message_instructs_verbatim_quoting_and_the_word_cap():
    report = ReportInput(url="https://example.org/r", title="t", body="b")
    system = build_messages(report)[0]["content"]
    assert "verbatim" in system.lower()
    assert "40 word" in system.lower()
    assert "presence_declared" in system
    assert "amount_basis" in system


def test_system_message_says_known_districts_are_context_not_evidence():
    report = ReportInput(url="https://example.org/r", title="t", body="b", known_districts=("Rasuwa", "Nuwakot"))
    system = build_messages(report)[0]["content"]
    assert "Rasuwa" in system and "Nuwakot" in system
    assert "not evidence" in system.lower()


def test_system_message_says_no_known_districts_when_there_are_none():
    report = ReportInput(url="https://example.org/r", title="t", body="b")
    system = build_messages(report)[0]["content"]
    assert "none known" in system.lower()


def test_user_message_contains_the_report_body():
    report = ReportInput(url="https://example.org/r", title="Flood report", body="IFRC responded with aid.")
    user = build_messages(report)[1]["content"]
    assert "IFRC responded with aid." in user
    assert "Flood report" in user


def test_statement_tool_schema_mirrors_response_statement_fields():
    props = STATEMENT_TOOL["function"]["parameters"]["properties"]["statements"]["items"]["properties"]
    for field in (
        "org_name_raw",
        "activity",
        "activity_type",
        "where_raw",
        "happened_on",
        "amount",
        "currency",
        "amount_basis",
        "quote",
    ):
        assert field in props


def test_statement_tool_enums_come_from_core_enums():
    from core import enums

    props = STATEMENT_TOOL["function"]["parameters"]["properties"]["statements"]["items"]["properties"]
    assert props["activity_type"]["enum"] == list(enums.ACTIVITY_TYPE)
    assert props["amount_basis"]["enum"] == list(enums.AMOUNT_BASIS)


# --- client.cost_usd -------------------------------------------------------------------------------


def test_cost_usd_uses_the_pinned_price_table():
    # $2/M in, $10/M out for anthropic/claude-sonnet-5 (read 2026-08-28).
    cost = cost_usd("anthropic/claude-sonnet-5", tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost == Decimal("12")


def test_cost_usd_scales_with_tokens():
    cost = cost_usd("anthropic/claude-sonnet-5", tokens_in=5_000, tokens_out=1_000)
    assert cost == (Decimal(5_000) * Decimal("2") + Decimal(1_000) * Decimal("10")) / Decimal(1_000_000)


def test_cost_usd_is_zero_for_an_unpriced_model():
    assert cost_usd("some/unknown-model", tokens_in=1_000_000, tokens_out=1_000_000) == Decimal("0")


# --- extract_statements job -----------------------------------------------------------------------


@dataclass
class _StubExtract:
    """Records every call and returns queued results in order (the last one repeats)."""

    results: list

    def __post_init__(self):
        self.calls: list[ReportInput] = []

    async def __call__(self, report: ReportInput, **kwargs) -> ExtractionResult:
        self.calls.append(report)
        index = min(len(self.calls) - 1, len(self.results) - 1)
        outcome = self.results[index]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _claim(**overrides) -> dict:
    base = {
        "org_name_raw": "IFRC",
        "activity": "released emergency funding",
        "activity_type": "cash_assistance",
        "where_raw": [],
        "happened_on": None,
        "amount": None,
        "currency": None,
        "amount_basis": "reported",
        "quote": "IFRC released emergency funding for the response.",
    }
    base.update(overrides)
    return base


async def _make_report(session, *, url: str, body: str, attempts: int = 0, glide_id: str | None = None) -> Report:
    report = Report(
        url=url, title="Test report", body_text=body, extraction_attempts=attempts, disaster_glide_id=glide_id
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def _latest_run(session) -> IngestionRun:
    return await session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))


async def test_extract_statements_writes_an_auto_statement_for_a_verbatim_claim(job_sessionmaker, session, monkeypatch):
    body = "IFRC released emergency funding for the response."
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body=body)

    stub = _StubExtract(
        [ExtractionResult(claims=[_claim(quote=body)], tokens_in=100, tokens_out=50, cost_usd=Decimal("0.001"))]
    )
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)

    rows = (await session.execute(select(ResponseStatement))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "auto"
    assert rows[0].quote == body
    assert rows[0].prompt_version == PROMPT_VERSION
    assert rows[0].verification == "third_party_reported"
    assert rows[0].org_id is None  # match_orgs's job, not this one's


async def test_extract_statements_writes_a_rejected_row_for_a_hallucinated_quote(
    job_sessionmaker, session, monkeypatch
):
    body = "IFRC released emergency funding for the response."
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body=body)

    stub = _StubExtract([ExtractionResult(claims=[_claim(quote="we rescued 4000 people from the roof")])])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)

    rows = (await session.execute(select(ResponseStatement))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "rejected_unverbatim"


async def test_extraction_attempts_is_incremented_before_the_call_not_after(job_sessionmaker, session, monkeypatch):
    """A crash mid-call must still leave the attempt counted, or a permanently-failing report
    would be retried forever."""
    async with job_sessionmaker() as write:
        report = await _make_report(write, url="https://example.org/1", body="text")

    stub = _StubExtract([RuntimeError("openrouter is down")])
    monkeypatch.setattr(llm_client, "extract", stub)

    with pytest.raises(RuntimeError, match="openrouter is down"):
        await extract_statements(job_sessionmaker)

    refreshed = await session.get(Report, report.id)
    await session.refresh(refreshed)
    assert refreshed.extraction_attempts == 1

    run = await _latest_run(session)
    assert run.status == "failed"


async def test_a_report_with_three_attempts_is_never_selected(job_sessionmaker, session, monkeypatch):
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body="text", attempts=MAX_ATTEMPTS)

    stub = _StubExtract([ExtractionResult(claims=[])])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)

    assert stub.calls == []
    run = await _latest_run(session)
    assert run.status == "succeeded"


async def test_max_reports_per_run_caps_how_many_reports_are_processed(job_sessionmaker, session, monkeypatch):
    async with job_sessionmaker() as write:
        for i in range(5):
            await _make_report(write, url=f"https://example.org/{i}", body="text")

    stub = _StubExtract([ExtractionResult(claims=[])])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker, max_reports=2)

    assert len(stub.calls) == 2


async def test_the_cost_cap_stops_the_loop_and_the_run_still_succeeds(job_sessionmaker, session, monkeypatch):
    async with job_sessionmaker() as write:
        for i in range(5):
            await _make_report(write, url=f"https://example.org/{i}", body="text")

    # Each call reports spending the whole cap, so the second report must never be processed.
    stub = _StubExtract([ExtractionResult(claims=[], tokens_in=0, tokens_out=0, cost_usd=Decimal("1.00"))])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker, max_reports=5, max_cost_usd=Decimal("1.00"))

    assert len(stub.calls) == 1
    run = await _latest_run(session)
    assert run.status == "succeeded"
    assert run.cost_usd == Decimal("1.0000")


async def test_a_report_already_extracted_at_this_prompt_version_is_not_re_billed(
    job_sessionmaker, session, monkeypatch
):
    """The cache is keyed on (body_sha256, prompt_version): re-running the job over an unchanged
    body under the same prompt_version must not call the model again."""
    body = "IFRC released emergency funding for the response."
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body=body)

    stub = _StubExtract([ExtractionResult(claims=[_claim(quote=body)], cost_usd=Decimal("0.001"))])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)
    assert len(stub.calls) == 1

    await extract_statements(job_sessionmaker)
    assert len(stub.calls) == 1  # no second call: this report is already cached


async def test_the_second_identical_run_writes_zero_new_rows(job_sessionmaker, session, monkeypatch):
    body = "IFRC released emergency funding for the response."
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body=body)

    stub = _StubExtract([ExtractionResult(claims=[_claim(quote=body)], cost_usd=Decimal("0.001"))])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)
    first_count = await session.scalar(select(func.count()).select_from(ResponseStatement))
    assert first_count == 1

    await extract_statements(job_sessionmaker)
    second_count = await session.scalar(select(func.count()).select_from(ResponseStatement))
    assert second_count == 1  # unchanged: no duplicate row

    second_run = await _latest_run(session)
    assert second_run.rows_written == 0


async def test_known_districts_are_passed_from_already_resolved_statements_on_the_same_disaster(
    job_sessionmaker, session, monkeypatch
):
    async with job_sessionmaker() as write:
        write.add(Disaster(glide_id="ff-2026-000162-npl", name="Nepal floods", country_iso3="NPL"))
        write.add(District(code="NP0329", name="Rasuwa", admin1_code="P3", admin1_name="Bagmati"))
        await write.commit()

        already_extracted = Report(
            url="https://example.org/already",
            body_text="earlier report",
            disaster_glide_id="ff-2026-000162-npl",
        )
        write.add(already_extracted)
        await write.commit()
        await write.refresh(already_extracted)

        statement = ResponseStatement(
            report_id=already_extracted.id,
            org_name_raw="IFRC",
            activity="responded",
            activity_type="other",
            quote="IFRC responded in Rasuwa.",
            verification="third_party_reported",
            model="test",
            prompt_version=PROMPT_VERSION,
            status="auto",
            content_hash="seed",
        )
        write.add(statement)
        await write.commit()
        await write.refresh(statement)
        write.add(StatementDistrict(statement_id=statement.id, district_code="NP0329", resolution="stated"))
        await write.commit()

        await _make_report(write, url="https://example.org/new", body="new report text", glide_id="ff-2026-000162-npl")

    stub = _StubExtract([ExtractionResult(claims=[])])
    monkeypatch.setattr(llm_client, "extract", stub)

    await extract_statements(job_sessionmaker)

    new_report_call = next(c for c in stub.calls if c.url == "https://example.org/new")
    assert "Rasuwa" in new_report_call.known_districts


async def test_extract_statements_closes_a_crashed_run_as_failed(job_sessionmaker, session, monkeypatch):
    async with job_sessionmaker() as write:
        await _make_report(write, url="https://example.org/1", body="text")

    async def boom(report, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(llm_client, "extract", boom)

    with pytest.raises(ValueError, match="boom"):
        await extract_statements(job_sessionmaker)

    run = await _latest_run(session)
    assert run.status == "failed"
    assert "boom" in run.error
