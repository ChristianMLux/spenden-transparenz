"""The product rules that live in the database.

A provenance rule enforced only in application code is a rule that a future job will forget. These
tests prove Postgres refuses the rows the product must never contain.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from core import enums
from core.models import (
    Base,
    Disaster,
    IngestionRun,
    Organisation,
    OrgDatum,
    Report,
    ResponseStatement,
)
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError


async def _org(session, org_id: str = "test-org") -> Organisation:
    org = Organisation(org_id=org_id, name_common="Test Org", org_type="ingo", hq_country="NP")
    session.add(org)
    await session.flush()
    return org


async def _datum(session, org_id: str = "test-org", path: str = "financial_transparency.income", **kw) -> OrgDatum:
    fields: dict = {
        "org_id": org_id,
        "path": path,
        "value": None,
        "source_url": None,
        "note": None,
        "gap_reason": None,
        "verification": "unverified",
        "content_hash": uuid.uuid4().hex,
    }
    fields.update(kw)
    row = OrgDatum(**fields)
    session.add(row)
    await session.flush()
    return row


async def _statement(session, **kw) -> ResponseStatement:
    disaster = Disaster(glide_id=f"ff-{uuid.uuid4().hex[:8]}", name="Test flood", country_iso3="NPL")
    session.add(disaster)
    report = Report(url=f"https://reliefweb.int/report/{uuid.uuid4().hex}", disaster_glide_id=disaster.glide_id)
    session.add(report)
    await session.flush()
    fields: dict = {
        "report_id": report.id,
        "org_name_raw": "Some Org",
        "activity": "distributed tarpaulins",
        "activity_type": "relief_distribution",
        "quote": "distributed 500 tarpaulins",
        "verification": "third_party_reported",
        "model": "claude-sonnet-5",
        "prompt_version": "v2",
        "status": "auto",
        "content_hash": uuid.uuid4().hex,
    }
    fields.update(kw)
    row = ResponseStatement(**fields)
    session.add(row)
    await session.flush()
    return row


# --- the provenance invariant, enforced by the database ------------------------------------


async def test_a_value_without_a_source_url_is_rejected(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_provenance"):
        await _datum(session, value={"amount": 1}, source_url=None)


async def test_a_gap_without_a_gap_reason_is_rejected(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_provenance"):
        await _datum(session, value=None, note="not found", gap_reason=None)


async def test_a_gap_without_a_note_is_rejected(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_provenance"):
        await _datum(session, value=None, note=None, gap_reason="searched_not_found")


async def test_a_value_carrying_datum_may_not_also_claim_a_gap_reason(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_provenance"):
        await _datum(session, value=1, source_url="https://example.org/x", gap_reason="not_public")


async def test_a_complete_gap_is_accepted_and_is_gap_is_true(session):
    await _org(session)
    row = await _datum(session, value=None, note="Register unreachable", gap_reason="source_unreachable")
    await session.refresh(row)
    assert row.is_gap is True


async def test_a_complete_value_is_accepted_and_is_gap_is_false(session):
    await _org(session)
    row = await _datum(session, value=1234, source_url="https://example.org/report.pdf", value_type="money")
    await session.refresh(row)
    assert row.is_gap is False


async def test_an_unknown_gap_reason_is_rejected(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_gap_reason"):
        await _datum(session, value=None, note="x", gap_reason="dog_ate_it")


async def test_an_unknown_verification_is_rejected(session):
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_verification"):
        await _datum(session, value=1, source_url="https://example.org/x", verification="trust_me")


# --- append-only history --------------------------------------------------------------------


async def test_two_current_rows_for_the_same_path_are_rejected(session):
    await _org(session)
    await _datum(session, value=1, source_url="https://example.org/a")
    with pytest.raises(IntegrityError, match="uq_org_datum_current"):
        await _datum(session, value=2, source_url="https://example.org/b")


async def test_a_superseded_row_does_not_block_a_new_current_row(session):
    await _org(session)
    old = await _datum(session, value=1, source_url="https://example.org/a")
    old.superseded_at = datetime.now(UTC)
    await session.flush()
    new = await _datum(session, value=2, source_url="https://example.org/b")
    rows = (await session.execute(select(OrgDatum).where(OrgDatum.org_id == "test-org"))).scalars().all()
    assert len(rows) == 2
    assert sum(1 for r in rows if r.superseded_at is None) == 1
    assert new.superseded_at is None


# --- gaps are SQL NULL, never JSON null -----------------------------------------------------


async def test_python_none_reaches_postgres_as_sql_null(session):
    """Regression guard. Without JSONB(none_as_null=True), SQLAlchemy writes the JSON literal
    'null' for a None value, is_gap comes back false, and every gap in the dataset is silently
    stored as a value. This failed on the first run against Postgres 16."""
    await _org(session)
    await _datum(session, path="names.legal", value=None, note="not found", gap_reason="searched_not_found")
    row = (
        await session.execute(
            text("select value is null as sql_null, is_gap from org_datum where path = 'names.legal'")
        )
    ).one()
    assert row.sql_null is True
    assert row.is_gap is True


async def test_a_gap_stored_as_json_null_would_not_count_as_a_gap(session):
    """Documents the trap: 'null'::jsonb is not SQL NULL, so is_gap would be false and the
    provenance CHECK would demand a source_url. Loaders must pass Python None."""
    await _org(session)
    with pytest.raises(IntegrityError, match="ck_org_datum_provenance"):
        await session.execute(
            text(
                "insert into org_datum (org_id, path, value, verification, content_hash, note, gap_reason)"
                " values ('test-org', 'p', 'null'::jsonb, 'unverified', 'h', 'n', 'not_public')"
            )
        )


# --- statements ------------------------------------------------------------------------------


async def test_a_quote_longer_than_40_words_is_rejected(session):
    with pytest.raises(IntegrityError, match="ck_response_statement_quote_words"):
        await _statement(session, quote=" ".join(["word"] * 41))


async def test_a_quote_of_exactly_40_words_is_accepted(session):
    row = await _statement(session, quote=" ".join(["word"] * 40))
    assert row.id is not None


async def test_an_amount_without_a_currency_is_rejected(session):
    with pytest.raises(IntegrityError, match="ck_response_statement_amount_currency"):
        await _statement(session, amount=1000000, currency=None)


async def test_an_amount_carries_the_basis_it_was_reported_on(session):
    """ "Pledged" and "paid" are different claims, and the pilot data has zero disbursed amounts.
    Without this column the board would render a pledge and a payment identically, which is the
    single most misleading thing this product could do."""
    row = await _statement(session, amount=1000000, currency="CHF", amount_basis="pledged")
    assert row.amount_basis == "pledged"


async def test_amount_basis_defaults_to_a_claim_free_value(session):
    row = await _statement(session)
    await session.refresh(row)
    assert row.amount_basis == "reported"


async def test_an_unknown_amount_basis_is_rejected(session):
    with pytest.raises((IntegrityError, DBAPIError), match="ck_response_statement_amount_basis"):
        await _statement(session, amount_basis="paid_probably")


async def test_disbursed_is_an_allowed_value_even_though_the_pilot_data_has_none(session):
    """The dataset contains no disbursed amount. The enum still has to be able to say it, or the
    product can never report the one thing donors actually want to know."""
    row = await _statement(session, amount=500, currency="EUR", amount_basis="disbursed")
    assert row.amount_basis == "disbursed"


async def test_a_hand_researched_statement_may_have_no_quote(session):
    """The 44 researched responses in the pilot data came from structured pages, and 5 of them
    have no quotable sentence. Dropping those would lose real, sourced responses."""
    row = await _statement(session, quote=None, model="hand_research")
    assert row.quote is None


async def test_an_extracted_statement_may_not_have_no_quote(session):
    """A claim a model produced must show the sentence it came from. This is the database half of
    the verbatim gate: even if the pipeline let one through, the row cannot exist."""
    with pytest.raises((IntegrityError, DBAPIError), match="ck_response_statement_quote_required_for_extracted"):
        await _statement(session, quote=None, model="claude-sonnet-5")


async def test_the_40_word_rule_still_applies_to_hand_researched_quotes(session):
    with pytest.raises(IntegrityError, match="ck_response_statement_quote_words"):
        await _statement(session, quote=" ".join(["word"] * 41), model="hand_research")


async def test_a_run_may_be_queued(session):
    """The admin endpoint records a queued run and returns; the pipeline drains it on its next
    tick. The API never runs a job inside a web request."""
    run = IngestionRun(job="ingest_orgs", status="queued")
    session.add(run)
    await session.flush()
    assert run.status == "queued"


async def test_a_statement_may_have_no_org_id(session):
    """Named but not identified stays visible. That is a designed state, not a failure."""
    row = await _statement(session, org_id=None, org_name_raw="Local youth club, Timure")
    assert row.org_id is None


async def test_the_same_statement_twice_in_one_report_is_rejected(session):
    first = await _statement(session)
    with pytest.raises(IntegrityError, match="uq_response_statement_content"):
        await _statement(session, report_id=first.report_id, content_hash=first.content_hash)


async def test_an_unknown_activity_type_is_rejected(session):
    with pytest.raises((IntegrityError, DBAPIError), match="ck_response_statement_activity_type"):
        await _statement(session, activity_type="saved_the_day")


# --- runs -------------------------------------------------------------------------------------


async def test_an_ingestion_run_gets_a_uuid_and_a_start_time(session):
    run = IngestionRun(job="seed_reference", status="running")
    session.add(run)
    await session.flush()
    await session.refresh(run)
    assert isinstance(run.id, uuid.UUID)
    assert run.started_at is not None
    assert run.rows_written == 0


# --- schema-wide rules -------------------------------------------------------------------------


def test_all_fourteen_tables_are_mapped():
    assert sorted(Base.metadata.tables) == [
        "disaster",
        "district",
        "district_alias",
        "ingestion_run",
        "org_alias",
        "org_datum",
        "org_registration",
        "org_warning",
        "organisations",
        "report",
        "report_source",
        "response_statement",
        "source",
        "statement_district",
    ]


def test_no_table_has_a_score_or_rating_column():
    banned = {"score", "rating", "rank", "grade", "tier"}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not (banned & set(column.name.split("_"))), f"{table.name}.{column.name} implies a ranking"


def test_body_text_exists_only_on_report():
    holders = sorted(t.name for t in Base.metadata.tables.values() if "body_text" in t.columns)
    assert holders == ["report"]


def test_no_column_could_hold_a_natural_person():
    banned = {"trustee", "trustees", "person", "contact", "email", "author", "firstname", "lastname"}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not (banned & set(column.name.split("_"))), f"{table.name}.{column.name} may hold a person"


def test_every_enum_column_carries_a_check_constraint():
    """A TEXT column named after an enum with no CHECK is an enum in name only."""
    enum_columns = {
        ("organisations", "org_type"): enums.ORG_TYPE,
        ("org_datum", "verification"): enums.VERIFICATION,
        ("org_datum", "gap_reason"): enums.GAP_REASON,
        ("org_datum", "value_type"): enums.VALUE_TYPE,
        ("org_registration", "registry"): enums.REGISTRY,
        ("org_warning", "type"): enums.WARNING_TYPE,
        ("response_statement", "activity_type"): enums.ACTIVITY_TYPE,
        ("response_statement", "status"): enums.STATEMENT_STATUS,
        ("statement_district", "resolution"): enums.DISTRICT_RESOLUTION,
        ("ingestion_run", "status"): enums.RUN_STATUS,
    }
    for (table_name, column_name), values in enum_columns.items():
        table = Base.metadata.tables[table_name]
        expressions = [str(c.sqltext) for c in table.constraints if hasattr(c, "sqltext")]
        expected = enums.check_in(column_name, values)
        assert any(expected in e for e in expressions), f"{table_name}.{column_name} has no CHECK for its enum"


def test_no_native_postgres_enum_type_is_used():
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert type(column.type).__name__ != "ENUM", f"{table.name}.{column.name} uses a native enum"
