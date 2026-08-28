"""ingest_orgs: the 44-organisation pilot dataset, idempotently, with append-only history.

Numbers asserted here are measured against this checkout (2026-08-28), the same way
pipeline/tests/test_seed_reference.py pins seed_reference's counts. Two of them differ from the
WP-A brief and are flagged rather than silently matched:

- Of the 420 org_datum nodes, 157 carry a JSON value in the source data, but 7 of those are
  nepal_presence.mode = "unknown" with source_url null - a value-shaped enum sentinel with no
  source, which core.models.OrgDatum's ck_org_datum_provenance CHECK will not accept as a value.
  ingest_orgs reclassifies those 7 into gaps (see pipeline/jobs/orgs.py's module docstring and
  test_the_seven_unsourced_unknown_mode_datums_are_reclassified_as_gaps below), so the database
  ends up with 150 non-gap datums and 270 gaps, not the brief's 157/263. Flagged to the backend
  lead as a data bug pending a source-data fix; this is the number that actually happens today.
- 56 registration rows carry a null identifier (22 source_unreachable, 34 searched_not_found),
  not the brief's 57/23. The top-line counts (44/14/420) all match the brief exactly.
"""

from __future__ import annotations

from datetime import date

import pytest
from core.models import IngestionRun, OrgAlias, Organisation, OrgDatum, OrgRegistration
from sqlalchemy import func, select, text

from pipeline.jobs.orgs import _partition_aliases, _value_type_and_extra, ingest_orgs, upsert_datum
from pipeline.jobs.seed_reference import seed_reference
from pipeline.runs import run_context

EXPECTED_ORGS = 44
EXPECTED_NP = 14
EXPECTED_DATUMS = 420
EXPECTED_VALUES = 150  # 157 in the JSON minus the 7 reclassified unknown-mode nodes
EXPECTED_GAPS = 270  # 263 in the JSON plus the 7 reclassified
EXPECTED_ALIASES = 100
EXPECTED_REGISTRATIONS_NULL_IDENTIFIER = 56


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
    assert run.rows_written == EXPECTED_ORGS + EXPECTED_DATUMS + 75 + EXPECTED_ALIASES
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


# --- the reclassified unknown-mode gap, specifically ---------------------------------------------


async def test_the_seven_unsourced_unknown_mode_datums_are_reclassified_as_gaps(job_sessionmaker, session):
    """globalgiving, care-nepal, lutheran-world-federation-nepal, wateraid-nepal,
    vishwa-hindu-parishad-nepal, kiwanis-club-rupandehi-lumbini, the-rising-youth-club all carry
    nepal_presence.mode = "unknown" with source_url null in the source JSON - a value-shaped enum
    sentinel with no source. Storing that as a value would violate ck_org_datum_provenance, so
    ingest_orgs stores it as a gap instead."""
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
