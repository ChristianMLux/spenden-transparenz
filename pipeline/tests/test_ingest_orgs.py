"""ingest_orgs: the 44-organisation pilot dataset, idempotently, with append-only history.

Numbers asserted here are measured against this checkout (2026-08-28), the same way
pipeline/tests/test_seed_reference.py pins seed_reference's counts.

Schema v0.3 (commit ec94db3) made nepal_presence.mode's value nullable and converted the 7
records that used to carry value="unknown" with source_url null into real gaps with a
gap_reason, at the source - see pipeline/jobs/orgs.py's module docstring. Counts moved from
157 values / 263 gaps to 150 / 270 for that reason, not because ingest_orgs reinterprets
anything: a value ever arriving here without a source_url is now a bug ingest_orgs raises on,
not one it silently reclassifies (see test_a_value_without_a_source_url_fails_loudly below).

56 registration rows carry a null identifier (22 source_unreachable, 34 searched_not_found) -
also measured directly, per the backend lead's PO-0 correction: the WP-A brief's original 57/23
came from a gap_reason distribution measured before load_orgs deduplicated caritas-nepal.

response_statement (added 2026-08-28, per the backend lead): the 44 current_response entries
across 39 distinct source_urls (also measured directly), loaded as hand-researched statements so
the Response Board has real data before WP-B's extraction pipeline has run. See
pipeline/jobs/orgs.py's module docstring for why body_text/title/format stay NULL on these
reports.

activity_type/amount_basis (schema v0.4, 2026-08-28): read from the record, never derived. A
keyword heuristic here got 14 of the 44 wrong, three of them by inventing a financial claim on a
sentence with no amount at all - see pipeline/jobs/orgs.py's module docstring for the full story.
The classification is data now (pipeline/migrations/explicit_classification.py); this loader's
only remaining decision is the fallback when a record has none (DEFAULT_ACTIVITY_TYPE /
DEFAULT_AMOUNT_BASIS), tested directly below.
"""

from __future__ import annotations

from datetime import date

import pytest
from core.models import (
    Disaster,
    IngestionRun,
    OrgAlias,
    Organisation,
    OrgDatum,
    OrgRegistration,
    Report,
    ResponseStatement,
)
from sqlalchemy import func, select, text

from pipeline.jobs.orgs import (
    DEFAULT_ACTIVITY_TYPE,
    DEFAULT_AMOUNT_BASIS,
    FLOOD_GLIDE_ID,
    _datum_row,
    _partition_aliases,
    _response_statement_row,
    _value_type_and_extra,
    ingest_orgs,
    upsert_datum,
)
from pipeline.jobs.seed_reference import seed_reference
from pipeline.runs import run_context

EXPECTED_ORGS = 44
EXPECTED_NP = 14
EXPECTED_DATUMS = 420
EXPECTED_VALUES = 150
EXPECTED_GAPS = 270
EXPECTED_ALIASES = 100
EXPECTED_REGISTRATIONS_NULL_IDENTIFIER = 56
EXPECTED_REPORTS = 39
EXPECTED_STATEMENTS = 44


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


async def _count_where(session, model, *where) -> int:
    return await session.scalar(select(func.count()).select_from(model).where(*where))


async def _latest_run(session, job: str = "ingest_orgs") -> IngestionRun:
    return await session.scalar(
        select(IngestionRun).where(IngestionRun.job == job).order_by(IngestionRun.started_at.desc()).limit(1)
    )


# --- ingest_orgs: counts, idempotency, history --------------------------------------------------


async def test_ingest_writes_44_orgs_14_nepalese_and_420_datums(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, Organisation) == EXPECTED_ORGS
    assert await _count_where(session, Organisation, Organisation.hq_country == "NP") == EXPECTED_NP
    assert await _count(session, OrgDatum) == EXPECTED_DATUMS
    assert await _count_where(session, OrgDatum, OrgDatum.is_gap.is_(False)) == EXPECTED_VALUES


async def test_second_run_writes_zero_rows(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    await ingest_orgs(job_sessionmaker)
    run = await _latest_run(session)
    assert run.rows_written == 0
    assert run.status == "succeeded"


async def test_the_run_closes_with_the_counts_it_wrote(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    run = await _latest_run(session)
    # organisations + datums + registrations + aliases (warnings: dataset has none today)
    # + 1 disaster + reports + response_statements
    assert (
        run.rows_written
        == EXPECTED_ORGS + EXPECTED_DATUMS + 75 + EXPECTED_ALIASES + 1 + EXPECTED_REPORTS + EXPECTED_STATEMENTS
    )
    assert run.rows_written > 0
    assert run.status == "succeeded"


async def test_a_changed_value_supersedes_rather_than_overwrites(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    await upsert_datum(
        session,
        org_id="unicef-nepal",
        path="financial_transparency.income",
        value=1,
        source_url="https://example.org/new",
    )
    rows = (
        (
            await session.execute(
                select(OrgDatum).where(
                    OrgDatum.org_id == "unicef-nepal", OrgDatum.path == "financial_transparency.income"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert sum(row.superseded_at is None for row in rows) == 1
    current = next(row for row in rows if row.superseded_at is None)
    assert current.value == 1
    assert current.source_url == "https://example.org/new"


async def test_a_gap_is_stored_as_sql_null_not_json_null(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    n = await session.scalar(text("select count(*) from org_datum where value is null"))
    assert n == EXPECTED_GAPS
    assert await session.scalar(text("select count(*) from org_datum where value = 'null'::jsonb")) == 0


async def test_ingest_orgs_never_deletes_a_datum_row(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    before = await _count(session, OrgDatum)
    await upsert_datum(
        session,
        org_id="unicef-nepal",
        path="financial_transparency.income",
        value=2,
        source_url="https://example.org/newer",
    )
    after = await _count(session, OrgDatum)
    assert after == before + 1


# --- the seven formerly-unsourced unknown-mode datums: now real gaps, at the source --------------


async def test_the_seven_previously_unsourced_unknown_mode_datums_are_real_gaps_from_the_source(
    job_sessionmaker, session
):
    """globalgiving, care-nepal, lutheran-world-federation-nepal, wateraid-nepal,
    vishwa-hindu-parishad-nepal, kiwanis-club-rupandehi-lumbini, the-rising-youth-club used to
    carry nepal_presence.mode = "unknown" with source_url null. Schema v0.3 and
    pipeline/migrations/nullable_presence_mode.py fixed this at the source: the JSON itself now
    has value=null + gap_reason for all seven, so this is no longer ingest_orgs reclassifying
    anything - it is the ordinary gap path, exercised on these specific records as a regression
    check that the source-data fix actually landed."""
    await ingest_orgs(job_sessionmaker)
    org_ids = (
        "globalgiving",
        "care-nepal",
        "lutheran-world-federation-nepal",
        "wateraid-nepal",
        "vishwa-hindu-parishad-nepal",
        "kiwanis-club-rupandehi-lumbini",
        "the-rising-youth-club",
    )
    for org_id in org_ids:
        row = await session.scalar(
            select(OrgDatum).where(
                OrgDatum.org_id == org_id, OrgDatum.path == "nepal_presence.mode", OrgDatum.superseded_at.is_(None)
            )
        )
        assert row is not None, org_id
        assert row.value is None, org_id
        assert row.is_gap is True, org_id
        assert row.gap_reason in ("not_searched", "searched_not_found", "source_unreachable", "not_public"), org_id
        assert row.note, org_id


# --- a value without a source is a bug ingest_orgs refuses, never reinterprets --------------------


def test_a_value_without_a_source_url_fails_loudly():
    """Rewriting research data on the way into the database is exactly the kind of silent
    correction this product exists not to make. If an unsourced value ever appears again,
    ingest_orgs must raise, not reclassify it into a gap."""
    datum = {"value": "unknown", "source_url": None, "retrieved_at": "2026-08-28", "verification": "unverified"}
    with pytest.raises(ValueError, match="has no source_url"):
        _datum_row("some-org", "nepal_presence.mode", datum, set(), run_id=None)


def test_a_value_with_a_source_url_is_never_rejected():
    """The failure is specific to "value present, source absent" - an ordinary sourced value must
    still pass through untouched."""
    datum = {
        "value": "own_staff",
        "source_url": "https://example.org/report",
        "retrieved_at": "2026-08-28",
        "verification": "self_reported",
    }
    row = _datum_row("some-org", "nepal_presence.mode", datum, set(), run_id=None)
    assert row["value"] == "own_staff"
    assert row["gap_reason"] is None


# --- org_registration: honest nulls stay in the record -------------------------------------------


async def test_registrations_are_written_and_null_identifiers_stay(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    total = await _count(session, OrgRegistration)
    assert total == 75
    null_identifier = await _count_where(session, OrgRegistration, OrgRegistration.identifier.is_(None))
    assert null_identifier == EXPECTED_REGISTRATIONS_NULL_IDENTIFIER
    null_id = OrgRegistration.identifier.is_(None)
    unreachable = OrgRegistration.gap_reason == "source_unreachable"
    not_found = OrgRegistration.gap_reason == "searched_not_found"
    assert await _count_where(session, OrgRegistration, null_id, unreachable) == 22
    assert await _count_where(session, OrgRegistration, null_id, not_found) == 34


async def test_registrations_are_idempotent_on_a_second_run(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, OrgRegistration) == 75


async def test_a_changed_registration_adds_a_row_rather_than_overwriting(job_sessionmaker, session):
    """org_registration has no superseded_at: content_hash is part of its unique key, so a changed
    registration is a new row by construction, and the old one is never touched or deleted."""
    await ingest_orgs(job_sessionmaker)
    before = await _count_where(session, OrgRegistration, OrgRegistration.org_id == "nepal-red-cross-society")

    new_registration = OrgRegistration(
        org_id="nepal-red-cross-society",
        registry="NP_SWC",
        identifier="NEW-ID-999",
        url=None,
        status=None,
        retrieved_at=date(2026, 8, 28),
        verification="register_confirmed",
        note="Manually re-researched",
        gap_reason=None,
        content_hash="deadbeef-test-only",
    )
    session.add(new_registration)
    await session.commit()

    after = await _count_where(session, OrgRegistration, OrgRegistration.org_id == "nepal-red-cross-society")
    assert after == before + 1


# --- org_alias -------------------------------------------------------------------------------


async def test_aliases_are_written_and_deduped(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, OrgAlias) == EXPECTED_ALIASES


async def test_aliases_are_idempotent_on_a_second_run(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, OrgAlias) == EXPECTED_ALIASES


async def test_every_alias_resolves_back_to_a_real_org(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    orphans = await session.scalar(
        text("select count(*) from org_alias a left join organisations o on o.org_id = a.org_id where o.org_id is null")
    )
    assert orphans == 0


def test_alias_collision_between_two_different_orgs_is_flagged_not_silently_dropped():
    """No real collision exists in the current 44-org dataset (measured directly), so this
    exercises the partition function with synthetic input rather than the real batch files -
    the logic still has to be right for the day a 45th organisation's name collides with an
    existing one."""
    candidates = [("world vision", "world-vision-nepal", "other"), ("world vision", "another-org", "other")]
    rows, collisions = _partition_aliases(candidates, existing={})
    assert rows == [{"alias_norm": "world vision", "org_id": "world-vision-nepal", "kind": "other"}]
    assert collisions == [("world vision", "world-vision-nepal", "another-org")]


def test_the_same_org_reasserting_its_own_alias_is_not_a_collision():
    candidates = [("unicef", "unicef-nepal", "other")]
    rows, collisions = _partition_aliases(candidates, existing={"unicef": "unicef-nepal"})
    assert rows == []
    assert collisions == []


def test_a_collision_against_an_existing_database_row_is_also_flagged():
    candidates = [("wv nepal", "world-vision-nepal", "other")]
    rows, collisions = _partition_aliases(candidates, existing={"wv nepal": "some-other-org"})
    assert rows == []
    assert collisions == [("wv nepal", "some-other-org", "world-vision-nepal")]


# --- value_type derivation ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("datum", "value", "expected_type"),
    [
        ({}, "United Nations Children's Fund", "string"),
        ({}, 2015, "integer"),
        ({}, True, "boolean"),
        ({}, None, None),
        ({"currency": "USD"}, 8263000000, "money"),
        ({"currency": None}, None, "money"),
    ],
)
def test_value_type_derivation(datum, value, expected_type):
    value_type, _extra = _value_type_and_extra(datum, value)
    assert value_type == expected_type


def test_money_extra_carries_currency_fiscal_year_and_scope():
    datum = {"currency": "USD", "fiscal_year": "2024", "scope": "global"}
    value_type, extra = _value_type_and_extra(datum, 8263000000)
    assert value_type == "money"
    assert extra == {"currency": "USD", "fiscal_year": "2024", "scope": "global"}


# --- report and response_statement: the 44 hand-researched current_response entries --------------


async def test_ingest_writes_44_response_statements_across_39_reports(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, Report) == EXPECTED_REPORTS
    assert await _count(session, ResponseStatement) == EXPECTED_STATEMENTS


async def test_response_statements_are_idempotent_on_a_second_run(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, Report) == EXPECTED_REPORTS
    assert await _count(session, ResponseStatement) == EXPECTED_STATEMENTS
    run = await _latest_run(session)
    assert run.rows_written == 0


async def test_every_hand_researched_statement_uses_the_hand_research_model_and_is_approved(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    rows = (await session.execute(select(ResponseStatement))).scalars().all()
    assert len(rows) == EXPECTED_STATEMENTS
    for row in rows:
        assert row.model == "hand_research"
        assert row.prompt_version == "research-2026-08-28"
        assert row.status == "approved"
        assert row.org_id is not None, "every hand-researched entry is already attributed to its org"


async def test_five_statements_have_no_quote_and_the_database_accepts_them(job_sessionmaker, session):
    """A quote-less row is only legal for model='hand_research' - core.models.ResponseStatement's
    ck_response_statement_quote_required_for_extracted CHECK enforces it. This test is really a
    check that the insert did not silently fail or get rejected by that constraint."""
    await ingest_orgs(job_sessionmaker)
    no_quote = await _count_where(session, ResponseStatement, ResponseStatement.quote.is_(None))
    assert no_quote == 5


async def test_every_report_disaster_glide_id_is_the_flood_and_body_text_is_never_set(job_sessionmaker, session):
    """These pages were read by a person, never fetched by this job - pretending otherwise would
    be exactly the dishonest provenance CLAUDE.md's Global Constraint 3 exists to prevent."""
    await ingest_orgs(job_sessionmaker)
    reports = (await session.execute(select(Report).where(Report.disaster_glide_id.is_not(None)))).scalars().all()
    hand_research_reports = [r for r in reports if r.body_text is None and r.body_sha256 is None]
    assert len(hand_research_reports) == EXPECTED_REPORTS
    for report in hand_research_reports:
        assert report.disaster_glide_id == FLOOD_GLIDE_ID
        assert report.body_text is None
        assert report.body_fetched_at is None


async def test_the_flood_disaster_row_exists_even_if_ingest_reliefweb_listing_never_ran(job_sessionmaker, session):
    """report.disaster_glide_id is a foreign key; ingest_orgs must not depend on
    ingest_reliefweb_listing having created the disaster row first."""
    await ingest_orgs(job_sessionmaker)
    disaster = await session.get(Disaster, FLOOD_GLIDE_ID)
    assert disaster is not None
    assert disaster.is_active is True


async def test_a_report_shared_by_two_organisations_gets_two_statements(job_sessionmaker, session):
    """care-nepal and community-self-reliance-centre both cite the same care.org press release
    (CARE Nepal names CSRC as a local partner in that release). One report row, two statements,
    each attributed to its own org - the report_id + content_hash unique key has to allow this."""
    await ingest_orgs(job_sessionmaker)
    url = "https://www.care.org/media-and-press/care-nepal-stands-ready-to-support-communities-affected-by-bhote-koshi-river-flash-flood/"
    report = await session.scalar(select(Report).where(Report.url == url))
    assert report is not None
    statements = (
        (await session.execute(select(ResponseStatement).where(ResponseStatement.report_id == report.id)))
        .scalars()
        .all()
    )
    org_ids = {s.org_id for s in statements}
    assert org_ids == {"care-nepal", "community-self-reliance-centre"}


async def test_response_statements_never_get_deleted(job_sessionmaker, session):
    await ingest_orgs(job_sessionmaker)
    before = await _count(session, ResponseStatement)
    await ingest_orgs(job_sessionmaker)
    after = await _count(session, ResponseStatement)
    assert after == before


# --- activity_type and amount_basis: read from the record, fall back when absent -----------------


async def test_every_statement_has_a_legal_activity_type_and_amount_basis(job_sessionmaker, session):
    """Schema v0.4 wrote activity_type/amount_basis for all 44 real entries
    (pipeline/migrations/explicit_classification.py, and its own tests read every value against
    the PO's classification). This is the read side: proves ingest_orgs actually picks the values
    up rather than silently falling back to "other"/"reported" for everything."""
    await ingest_orgs(job_sessionmaker)
    rows = (await session.execute(select(ResponseStatement))).scalars().all()
    assert len(rows) == EXPECTED_STATEMENTS
    fallback_only = [r for r in rows if r.activity_type == "other" and r.amount_basis == "reported"]
    # "other"/"reported" can be a legitimate explicit choice too, so this is a loose sanity bound,
    # not a claim that none of the 44 are legitimately "other" - just that the fallback path is
    # not silently swallowing everything.
    assert len(fallback_only) < EXPECTED_STATEMENTS


def test_response_statement_row_uses_the_explicit_classification():
    org = {"org_id": "some-org", "names": {"common": "Some Org"}}
    entry = {
        "what": "Distributed tarpaulins",
        "where": ["Rasuwa"],
        "date": "2026-08-27",
        "verification": "self_reported",
        "activity_type": "relief_distribution",
        "amount_basis": "released",
        "amount": 1000,
        "currency": "USD",
    }
    row = _response_statement_row(org, entry, report_id=1, run_id=None)
    assert row["activity_type"] == "relief_distribution"
    assert row["amount_basis"] == "released"


def test_response_statement_row_falls_back_when_the_record_has_no_classification():
    """The only thing left in this loader that decides anything, per the backend lead: an absent
    value falls back to DEFAULT_ACTIVITY_TYPE / DEFAULT_AMOUNT_BASIS, which claim nothing - never
    a guess. Schema v0.4 writes an explicit value for every real entry today, so this exercises a
    shape the loader has never actually seen against the pilot data - the fallback is what
    protects the day a new response_statement source arrives without a classification."""
    org = {"org_id": "some-org", "names": {"common": "Some Org"}}
    entry = {
        "what": "Something happened",
        "where": [],
        "date": None,
        "verification": "unverified",
    }
    row = _response_statement_row(org, entry, report_id=1, run_id=None)
    assert row["activity_type"] == DEFAULT_ACTIVITY_TYPE
    assert row["amount_basis"] == DEFAULT_AMOUNT_BASIS
    assert row["activity_type"] == "other"
    assert row["amount_basis"] == "reported"


# --- runs the whole pipeline once as a sanity check on the run contract itself -------------------


async def test_ingest_orgs_opens_and_closes_its_own_run_when_called_bare(job_sessionmaker, session):
    """The (session_factory, handle=None) re-entry from pipeline/jobs/seed_reference.py: calling
    ingest_orgs with no handle opens its own run_context rather than requiring every caller to."""
    await ingest_orgs(job_sessionmaker)
    run = await _latest_run(session)
    assert run is not None
    assert run.job == "ingest_orgs"
    assert run.finished_at is not None
    assert run.git_sha is not None


async def test_ingest_orgs_closes_its_run_as_failed_on_a_bad_session_factory(job_sessionmaker, session):
    """A job that raises still closes its run rather than leaving it "running" forever - the same
    contract pipeline/tests/test_seed_reference.py proves for run_context directly."""

    async def _broken_factory():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        async with run_context(job_sessionmaker, "ingest_orgs_broken"):
            await _broken_factory()

    run = await _latest_run(session, job="ingest_orgs_broken")
    assert run.status == "failed"
    assert run.finished_at is not None


# --- seed_reference must have run first in real operation, but ingest_orgs does not depend on it -


async def test_ingest_orgs_does_not_require_seed_reference_to_have_run_first(job_sessionmaker, session):
    """organisations/org_datum/org_alias/org_registration/org_warning have no foreign key into
    district or source, so ingest_orgs and seed_reference are independent - either can run first."""
    await ingest_orgs(job_sessionmaker)
    assert await _count(session, Organisation) == EXPECTED_ORGS
    await seed_reference(job_sessionmaker)
    assert await _count(session, Organisation) == EXPECTED_ORGS
