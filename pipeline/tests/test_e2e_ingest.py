"""The golden fixture and the WP-B end-to-end chain.

Five real ReliefWeb report bodies (data/raw/reliefweb/extraction_test_inputs.json, saved during the
research phase) plus a recorded model response (data/raw/reliefweb/extraction_test_output.json, the
same session's actual extraction test - the "21/21 verbatim with Sonnet" result the spec cites) are
frozen into pipeline/tests/fixtures/extract/. This test stubs the LLM with that recorded response,
so it is deterministic and free, and proves two things: every one of the 21 quotes is a real,
verbatim substring of its report (the fixture's whole reason to exist), and the chain of jobs this
work package owns - extract_statements, match_orgs, resolve_districts - is idempotent end to end.

WP-A owns ingest_reliefweb_listing and fetch_report_bodies. Those are not exercised here: this test
seeds `disaster` and `report` rows directly from the fixture (the shape WP-A's fetch_report_bodies
would have produced) rather than waiting for those jobs to land, per the WP-B brief. Once WP-A's
jobs are merged, prepending them (serving the fixture's listing/report pages over pytest-httpserver
instead of inserting rows directly) is a mechanical follow-up, not a redesign - the seam is exactly
the `report` table this test already writes to.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.models import Disaster, IngestionRun, Report, ResponseStatement, StatementDistrict
from sqlalchemy import func, select

import pipeline.extract.client as llm_client
from pipeline.extract.client import ExtractionResult
from pipeline.extract.prompt import ReportInput
from pipeline.jobs.districts import resolve_districts
from pipeline.jobs.extract import extract_statements
from pipeline.jobs.match import match_orgs
from pipeline.jobs.seed_reference import seed_reference

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "extract"
DISASTER_GLIDE_ID = "ff-2026-000162-npl"

REPORTS = json.loads((FIXTURES / "reports.json").read_text(encoding="utf-8"))
LLM_RESPONSES: dict[str, list[dict]] = json.loads((FIXTURES / "llm_response.json").read_text(encoding="utf-8"))

EXPECTED_TOTAL_CLAIMS = 21


def _decimal_claims(url: str) -> list[dict]:
    """The fixture stores amount as a string (JSON has no Decimal); convert back for the stub."""
    claims = []
    for claim in LLM_RESPONSES.get(url, []):
        claim = dict(claim)
        if claim["amount"] is not None:
            claim["amount"] = Decimal(claim["amount"])
        claims.append(claim)
    return claims


class _FixtureExtract:
    """Stands in for pipeline.extract.client.extract: looks the report up by URL in the recorded
    fixture instead of calling OpenRouter. The real API is never reachable from this test."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, report: ReportInput, **kwargs) -> ExtractionResult:
        self.calls.append(report.url)
        claims = _decimal_claims(report.url)
        return ExtractionResult(claims=claims, tokens_in=4000, tokens_out=800, cost_usd=Decimal("0.016"))


async def _seed_reports(session_factory) -> None:
    async with session_factory() as session:
        session.add(Disaster(glide_id=DISASTER_GLIDE_ID, name="Nepal floods 2026", country_iso3="NPL"))
        await session.commit()
        for item in REPORTS:
            session.add(
                Report(
                    url=item["url"],
                    title=item["title"],
                    format="html",
                    published_at=datetime.fromisoformat(item["published_at"]),
                    disaster_glide_id=DISASTER_GLIDE_ID,
                    body_text=item["body"],
                )
            )
        await session.commit()


async def _run_chain(job_sessionmaker, monkeypatch) -> _FixtureExtract:
    stub = _FixtureExtract()
    monkeypatch.setattr(llm_client, "extract", stub)
    await extract_statements(job_sessionmaker, max_reports=len(REPORTS), max_cost_usd=Decimal("1.00"))
    await match_orgs(job_sessionmaker)
    await resolve_districts(job_sessionmaker)
    return stub


async def _table_counts(session) -> dict[str, int]:
    return {
        "response_statement": await session.scalar(select(func.count()).select_from(ResponseStatement)),
        "statement_district": await session.scalar(select(func.count()).select_from(StatementDistrict)),
    }


async def test_the_fixture_is_five_reports_and_twenty_one_claims():
    """Sanity check on the frozen fixture itself, independent of any job."""
    assert len(REPORTS) == 5
    assert sum(len(claims) for claims in LLM_RESPONSES.values()) == EXPECTED_TOTAL_CLAIMS


async def test_21_of_21_recorded_claims_pass_the_verbatim_gate(job_sessionmaker, session, monkeypatch):
    """The gate criterion the spec names: every one of the 21 recorded quotes is a real, verbatim
    substring of its report - none hallucinated, none over 40 words, none silently softened."""
    await seed_reference(job_sessionmaker)
    await _seed_reports(job_sessionmaker)

    stub = await _run_chain(job_sessionmaker, monkeypatch)
    assert sorted(stub.calls) == sorted(item["url"] for item in REPORTS)

    rows = (await session.execute(select(ResponseStatement.status))).scalars().all()
    total = len(rows)
    auto = sum(1 for status in rows if status == "auto")
    rejected = total - auto

    assert total == EXPECTED_TOTAL_CLAIMS, f"expected {EXPECTED_TOTAL_CLAIMS} statements, got {total}"
    assert auto == EXPECTED_TOTAL_CLAIMS, f"{rejected} of {total} claims were rejected_unverbatim, expected 0"


async def test_the_chain_produces_statements_with_resolved_districts(job_sessionmaker, session, monkeypatch):
    await seed_reference(job_sessionmaker)
    await _seed_reports(job_sessionmaker)
    await _run_chain(job_sessionmaker, monkeypatch)

    district_count = await session.scalar(select(func.count()).select_from(StatementDistrict))
    assert district_count > 0

    rasuwa_stated = await session.scalar(
        select(func.count())
        .select_from(StatementDistrict)
        .where(StatementDistrict.district_code == "NP0329", StatementDistrict.resolution == "stated")
    )
    assert rasuwa_stated > 0, "expected at least one statement to state Rasuwa (NP0329) directly"


async def test_the_second_full_run_of_the_chain_writes_zero_new_rows(job_sessionmaker, session, monkeypatch):
    """The idempotency contract, chained across every job WP-B owns: extract_statements skips
    already-extracted reports via its cache, match_orgs never re-matches an unchanged statement,
    and resolve_districts never rewrites an unchanged resolution."""
    await seed_reference(job_sessionmaker)
    await _seed_reports(job_sessionmaker)

    first_stub = await _run_chain(job_sessionmaker, monkeypatch)
    assert len(first_stub.calls) == len(REPORTS)
    before = await _table_counts(session)
    assert before["response_statement"] == EXPECTED_TOTAL_CLAIMS

    second_stub = await _run_chain(job_sessionmaker, monkeypatch)
    assert second_stub.calls == [], "the cache must skip every already-extracted report on the second run"
    after = await _table_counts(session)

    assert after == before

    # The most recent run of each of WP-B's three jobs, not a positional split of every run row:
    # seed_reference also opens an ingestion_run, so runs[len(runs) // 2:] would not line up with
    # "the second _run_chain() call" and silently picked up the first run's resolve_districts row
    # instead - caught by this test itself before it shipped.
    for job in ("extract_statements", "match_orgs", "resolve_districts"):
        latest = await session.scalar(
            select(IngestionRun.rows_written)
            .where(IngestionRun.job == job)
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        assert latest == 0, f"second run of {job} wrote {latest} rows, expected 0"
