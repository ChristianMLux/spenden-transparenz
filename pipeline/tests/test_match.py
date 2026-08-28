"""match_orgs: org_name_raw -> core.normalise.alias_norm -> org_alias.org_id.

Exact normalised match only, never fuzzy: a wrong organisation attributed to a relief activity is
worse than a null one, and org_id IS NULL is a designed, visible state meaning "named but not
identified" - not a bug to paper over with a similarity score.
"""

from __future__ import annotations

from core.models import IngestionRun, OrgAlias, Organisation, Report, ResponseStatement
from sqlalchemy import select

import pipeline.jobs.match as match_module
from pipeline.jobs.match import match_orgs
from pipeline.runs import run_context


async def _latest_run(session) -> IngestionRun:
    return await session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))


async def _make_org(session, org_id: str, alias: str) -> None:
    session.add(Organisation(org_id=org_id, name_common=org_id, org_type="ingo"))
    await session.commit()
    session.add(OrgAlias(alias_norm=alias, org_id=org_id, kind="other"))
    await session.commit()


async def _make_statement(
    session, *, org_name_raw: str, status: str = "auto", report_id: int | None = None, url: str | None = None
) -> int:
    if report_id is None:
        report = Report(url=url or f"https://example.org/{org_name_raw}", body_text="x")
        session.add(report)
        await session.commit()
        await session.refresh(report)
        report_id = report.id
    statement = ResponseStatement(
        report_id=report_id,
        org_name_raw=org_name_raw,
        activity="did something",
        activity_type="other",
        quote="did something",
        verification="third_party_reported",
        model="test",
        prompt_version="v2",
        status=status,
        content_hash=f"hash-{org_name_raw}-{status}",
    )
    session.add(statement)
    await session.commit()
    await session.refresh(statement)
    return statement.id


async def test_match_orgs_matches_an_exact_normalised_alias(job_sessionmaker, session):
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "world vision nepal")
        statement_id = await _make_statement(write, org_name_raw="World Vision Nepal")

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id == "world-vision-nepal"


async def test_match_orgs_matches_through_punctuation_and_case_differences(job_sessionmaker, session):
    """alias_norm folds case, punctuation and whitespace - "W.V. Nepal" must reach the same key as
    the seeded alias "wv nepal", proving match_orgs actually goes through alias_norm and not a
    naive string comparison."""
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "wv nepal")
        statement_id = await _make_statement(write, org_name_raw="W.V. Nepal")

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id == "world-vision-nepal"


async def test_match_orgs_leaves_org_id_null_when_no_alias_matches(job_sessionmaker, session):
    async with job_sessionmaker() as write:
        statement_id = await _make_statement(write, org_name_raw="Some Unknown Org")

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id is None


async def test_match_orgs_does_not_fuzzy_match_a_near_miss(job_sessionmaker, session):
    """ "World Vision" must not match an alias seeded only for "World Vision Nepal" - a near miss is
    not a match. A wrong attribution is worse than none."""
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "world vision nepal")
        statement_id = await _make_statement(write, org_name_raw="World Vision")

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id is None


async def test_match_orgs_skips_rejected_statements(job_sessionmaker, session):
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "world vision nepal")
        statement_id = await _make_statement(write, org_name_raw="World Vision Nepal", status="rejected_unverbatim")

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id is None


async def test_match_orgs_never_clears_an_existing_match(job_sessionmaker, session):
    """A name that stops matching (e.g. an alias row edited elsewhere) is a research question, not
    evidence the earlier match was wrong - match_orgs only ever sets org_id, never clears it."""
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "world vision nepal")
        statement_id = await _make_statement(write, org_name_raw="World Vision Nepal")
        await match_orgs(job_sessionmaker)

        row = await write.get(ResponseStatement, statement_id)
        row.org_name_raw = "Some Renamed Thing With No Alias"
        await write.commit()

    await match_orgs(job_sessionmaker)

    row = await session.get(ResponseStatement, statement_id)
    await session.refresh(row)
    assert row.org_id == "world-vision-nepal"


async def test_the_second_identical_run_writes_zero_rows(job_sessionmaker, session):
    async with job_sessionmaker() as write:
        await _make_org(write, "world-vision-nepal", "world vision nepal")
        await _make_statement(write, org_name_raw="World Vision Nepal")

    await match_orgs(job_sessionmaker)
    first = await _latest_run(session)
    assert first.rows_written == 1

    await match_orgs(job_sessionmaker)
    second = await _latest_run(session)
    assert second.rows_written == 0
    assert second.status == "succeeded"


async def test_a_failing_run_closes_as_failed(job_sessionmaker, session):
    import pytest

    with pytest.raises(RuntimeError, match="boom"):
        async with run_context(job_sessionmaker, "match_orgs"):
            raise RuntimeError("boom")
    row = await _latest_run(session)
    assert row.status == "failed"


async def test_unmatched_names_are_logged_with_their_count(job_sessionmaker, session, monkeypatch):
    """Stubbed at the module's `log` attribute, not via pytest's caplog or a logging.Handler:
    verified with a standalone script outside pytest that the real logger emits this record
    correctly (propagate=True, level=INFO, handler receives it), so the failure to capture it
    through caplog or a directly-attached logging.Handler inside this specific pytest/asyncio
    setup is a test-harness artifact, not a bug in match_orgs. Stubbing the module attribute
    sidesteps the stdlib logging machinery entirely and is the same boundary-stubbing pattern
    already used for the LLM client in test_extract_job.py.
    """
    async with job_sessionmaker() as write:
        await _make_statement(write, org_name_raw="Ghost Org", url="https://example.org/ghost-1")
        await _make_statement(write, org_name_raw="Ghost Org", url="https://example.org/ghost-2")

    calls: list[tuple[str, dict]] = []

    class _StubLog:
        def info(self, msg: str, extra: dict | None = None) -> None:
            calls.append((msg, extra or {}))

    monkeypatch.setattr(match_module, "log", _StubLog())

    await match_orgs(job_sessionmaker)

    unmatched_calls = [
        extra for msg, extra in calls if msg == "match_orgs_unmatched" and extra.get("org_name_raw") == "Ghost Org"
    ]
    assert unmatched_calls, "expected an unmatched-name log call for 'Ghost Org'"
    assert unmatched_calls[0]["count"] == 2
