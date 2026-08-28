"""resolve_districts: where_raw[] -> district_alias -> statement_district(resolution="stated");
when a statement names no place, it inherits the districts already stated by sibling statements on
the same report, with resolution="inherited_from_report". The distinction survives to the API,
because "the organisation said Rasuwa" and "the report was about Rasuwa" are different claims.

district_alias is consumed as seeded by Phase 0's seed_reference (160 rows) rather than hand-built
here, so these tests exercise the real codes and the real UNRESOLVABLE phrases - no alias is added
by this file.
"""

from __future__ import annotations

from core.models import IngestionRun, Report, ResponseStatement, StatementDistrict
from sqlalchemy import select

from pipeline.jobs.districts import resolve_districts
from pipeline.jobs.seed_reference import UNRESOLVABLE, seed_reference


async def _latest_run(session) -> IngestionRun:
    return await session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))


async def _make_report(session, url: str) -> int:
    report = Report(url=url, body_text="x")
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report.id


async def _make_statement(session, *, report_id: int, where_raw: list[str], suffix: str) -> int:
    statement = ResponseStatement(
        report_id=report_id,
        org_name_raw="Some Org",
        activity="did something",
        activity_type="other",
        where_raw=where_raw,
        quote="did something",
        verification="third_party_reported",
        model="test",
        prompt_version="v2",
        status="auto",
        content_hash=f"hash-{report_id}-{suffix}",
    )
    session.add(statement)
    await session.commit()
    await session.refresh(statement)
    return statement.id


async def _districts_of(session, statement_id: int) -> dict[str, str]:
    rows = (
        await session.execute(
            select(StatementDistrict.district_code, StatementDistrict.resolution).where(
                StatementDistrict.statement_id == statement_id
            )
        )
    ).all()
    return dict(rows)


async def test_resolve_districts_resolves_a_named_place_as_stated(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        statement_id = await _make_statement(write, report_id=report_id, where_raw=["Rasuwa"], suffix="a")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, statement_id)
    assert districts == {"NP0329": "stated"}


async def test_resolve_districts_resolves_the_district_suffix_form(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        statement_id = await _make_statement(write, report_id=report_id, where_raw=["Nuwakot district"], suffix="a")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, statement_id)
    assert districts == {"NP0328": "stated"}


async def test_resolve_districts_resolves_a_settlement_alias(job_sessionmaker, session):
    """Timure -> NP0329 (Rasuwa): a settlement name, not a district name."""
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        statement_id = await _make_statement(write, report_id=report_id, where_raw=["Timure"], suffix="a")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, statement_id)
    assert districts == {"NP0329": "stated"}


async def test_resolve_districts_inherits_report_districts_when_the_statement_names_no_place(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        await _make_statement(write, report_id=report_id, where_raw=["Rasuwa"], suffix="a")
        silent_statement_id = await _make_statement(write, report_id=report_id, where_raw=[], suffix="b")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, silent_statement_id)
    assert districts == {"NP0329": "inherited_from_report"}


async def test_a_statement_with_no_place_and_no_sibling_resolution_gets_no_district_row(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        statement_id = await _make_statement(write, report_id=report_id, where_raw=[], suffix="a")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, statement_id)
    assert districts == {}


async def test_unresolvable_phrases_never_produce_a_district_row(job_sessionmaker, session):
    """A river corridor crosses several districts and "Nepal" is the whole country: picking one
    would invent a location the source never stated."""
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        statement_id = await _make_statement(write, report_id=report_id, where_raw=list(UNRESOLVABLE), suffix="a")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, statement_id)
    assert districts == {}


async def test_stated_resolution_is_not_overwritten_by_inheritance(job_sessionmaker, session):
    """A statement that names its own place (Nuwakot) must not also inherit a sibling's district
    (Rasuwa) - "the org said Nuwakot" must not blur into "the report was about Rasuwa"."""
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        await _make_statement(write, report_id=report_id, where_raw=["Rasuwa"], suffix="a")
        stated_statement_id = await _make_statement(write, report_id=report_id, where_raw=["Nuwakot"], suffix="b")

    await resolve_districts(job_sessionmaker)

    districts = await _districts_of(session, stated_statement_id)
    assert districts == {"NP0328": "stated"}


async def test_the_second_identical_run_writes_zero_new_rows(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        report_id = await _make_report(write, "https://example.org/1")
        await _make_statement(write, report_id=report_id, where_raw=["Rasuwa"], suffix="a")

    await resolve_districts(job_sessionmaker)
    first = await _latest_run(session)
    assert first.rows_written == 1

    await resolve_districts(job_sessionmaker)
    second = await _latest_run(session)
    assert second.rows_written == 0
    assert second.status == "succeeded"
