"""Load the 44-organisation pilot dataset into organisations, org_datum, org_alias,
org_registration and org_warning.

Five bulk passes for the whole batch, not 44 x 5 round trips: organisations and the alias table
each get one upsert statement, registrations and warnings each get one insert-or-skip statement,
and org_datum - the one table with append-only, supersede-on-change history rather than a mutable
row per key - gets one SELECT of current state plus one UPDATE to close out changed rows plus one
INSERT for new-or-changed rows. See pipeline/jobs/seed_reference.py:_upsert for the pattern the
mutable tables copy, and _upsert_org_datum_rows below for the versioned one.

Fixed at the source, not here (2026-08-28): 7 nepal_presence.mode nodes used to carry
value="unknown" with source_url null, because datum_presence_mode was the only datum type in the
schema whose value could not be null - "unknown" was the only word available to a researcher who
could not determine an organisation's mode. Schema v0.3 (commit ec94db3) makes value nullable
there too, and pipeline/migrations/nullable_presence_mode.py converted those 7 records into real
gaps with a gap_reason. ingest_orgs does not reclassify anything: rewriting research data on the
way into the database is exactly the kind of silent correction this product exists not to make.
If a value ever arrives here without a source_url, that is a data bug - _datum_row raises rather
than reinterpreting it, and the whole run fails loudly through run_context's exception handling.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from core.logging import get_logger
from core.models import OrgAlias, Organisation, OrgDatum, OrgRegistration, OrgWarning
from core.normalise import alias_norm
from sqlalchemy import func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.migrations.add_gap_reason import (
    GENERATED_NOTE,
    derive_gap_reason,
    derive_registration_gap_reason,
    load_orgs,
    normalise_path,
    walk_datums,
)
from pipeline.runs import RunHandle, run_context

log = get_logger("ingest_orgs")

ORG_COLUMNS = (
    "name_common",
    "org_type",
    "hq_country",
    "hq_city",
    "hq_source_url",
    "website",
    "last_updated",
    "research_notes",
)


def _content_hash(*values: Any) -> str:
    """sha256 over the canonical JSON of a fixed, documented tuple of fields. Same hash for the
    same content means skip; a different hash means the row has genuinely changed."""
    payload = json.dumps(list(values), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


# --- organisations -------------------------------------------------------------------------------


def _organisation_row(org: dict[str, Any], run_id: Any) -> dict[str, Any]:
    hq = org["hq"]
    return {
        "org_id": org["org_id"],
        "name_common": org["names"]["common"],
        "org_type": org["org_type"],
        "hq_country": hq["country"],
        "hq_city": hq.get("city"),
        "hq_source_url": hq.get("source_url"),
        "website": org.get("website"),
        "last_updated": _parse_date(org.get("last_updated")),
        "research_notes": org.get("research_notes"),
        "ingestion_run_id": run_id,
    }


async def _upsert(
    session: AsyncSession,
    model: type,
    rows: list[dict[str, Any]],
    key: str,
    columns: tuple[str, ...],
) -> int:
    """One statement for the whole batch. Returns the number of rows that actually changed.

    Copied from pipeline/jobs/seed_reference.py:_upsert. is_distinct_from in the WHERE handles
    NULLs correctly, so a row whose every compared column already matches is not rewritten and
    does not come back in RETURNING - which is what makes "second run writes zero rows" checkable.
    columns deliberately excludes ingestion_run_id: a row that did not change should not appear to
    have been touched by this run just because the run_id column would otherwise always differ.
    """
    if not rows:
        return 0
    statement = insert(model).values(rows)
    changed = or_(*[getattr(model, column).is_distinct_from(statement.excluded[column]) for column in columns])
    statement = statement.on_conflict_do_update(
        index_elements=[key],
        set_={column: statement.excluded[column] for column in columns},
        where=changed,
    ).returning(getattr(model, key))
    result = await session.execute(statement)
    return len(result.scalars().all())


# --- org_datum -------------------------------------------------------------------------------


def _value_type_and_extra(datum: dict[str, Any], value: Any) -> tuple[str | None, dict[str, Any]]:
    """value_type from the Python type of the stored value.

    Money datums (financial_transparency.income/expenditure) carry currency/fiscal_year/scope as
    sibling keys in the source JSON and are typed "money" regardless of value - including when
    value is a gap, since those three columns are still populated (usually all null) on that row.
    A non-money gap gets no value_type: value is None, and unlike money there is no structural
    indicator left in the source JSON to derive a type from.
    """
    if "currency" in datum:
        extra = {
            "currency": datum.get("currency"),
            "fiscal_year": datum.get("fiscal_year"),
            "scope": datum.get("scope"),
        }
        return "money", extra
    if isinstance(value, bool):
        return "boolean", {}
    if isinstance(value, int):
        return "integer", {}
    if isinstance(value, float):
        return "number", {}
    if isinstance(value, str):
        return "string", {}
    return None, {}


def _datum_row(org_id: str, path: str, datum: dict[str, Any], data_gaps: set[str], run_id: Any) -> dict[str, Any]:
    value = datum.get("value")
    source_url = datum.get("source_url")

    if value is not None and not source_url:
        # A value without a source is a data bug, not something to reinterpret on the way in -
        # see the module docstring. Fail loudly and immediately, before any row reaches the
        # database, rather than let a vague CHECK-constraint error surface later for a row buried
        # in a 420-row batch insert.
        raise ValueError(
            f"{org_id}.{path}: value {value!r} has no source_url. A datum with a value must have "
            "a source (CLAUDE.md Global Constraint 2); this is a bug in the source JSON to fix "
            "at the source, not something ingest_orgs should reclassify or reinterpret."
        )

    gap_reason = datum.get("gap_reason")
    note = datum.get("note")
    if value is None and gap_reason is None:
        gap_reason = derive_gap_reason({"value": None, "note": note}, path, data_gaps)
    if value is None and not (note or "").strip():
        note = GENERATED_NOTE.get(gap_reason, GENERATED_NOTE["not_searched"])

    value_type, extra = _value_type_and_extra(datum, value)
    retrieved_at_raw = datum.get("retrieved_at")
    verification = datum.get("verification") or "unverified"
    quote = datum.get("quote")

    content_hash = _content_hash(value, source_url, retrieved_at_raw, verification, quote, note, gap_reason)

    return {
        "org_id": org_id,
        "path": path,
        "value": value,
        "value_type": value_type,
        "currency": extra.get("currency"),
        "fiscal_year": extra.get("fiscal_year"),
        "scope": extra.get("scope"),
        "source_url": source_url,
        "retrieved_at": _parse_date(retrieved_at_raw),
        "quote": quote,
        "note": note,
        "verification": verification,
        "gap_reason": gap_reason,
        "content_hash": content_hash,
        "ingestion_run_id": run_id,
    }


async def _upsert_org_datum_rows(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Bulk supersede-then-insert. org_datum is append-only history, not a mutable row per key, so
    it cannot use a single INSERT ... ON CONFLICT DO UPDATE the way _upsert does: a changed row
    needs the OLD row closed out (superseded_at set) AND a NEW row inserted, and Postgres can only
    take one of those two paths per conflicting row in one statement.

    One SELECT to read current state (bounded to the org_ids in this batch, not the whole table),
    one UPDATE to close out the rows whose content actually changed, one INSERT for new-or-changed
    rows. Never one round trip per row: 420 datums is 3 statements here.

    This is not a per-request hot path - it runs from a manual/cron batch job over a dataset in
    the hundreds of rows, not thousands - so a bounded SELECT plus two bulk writes is the right
    shape rather than something that needs further batching.
    """
    if not rows:
        return 0

    org_ids = {r["org_id"] for r in rows}
    existing = await session.execute(
        select(OrgDatum.org_id, OrgDatum.path, OrgDatum.content_hash).where(
            OrgDatum.org_id.in_(org_ids), OrgDatum.superseded_at.is_(None)
        )
    )
    current_hash = {(org_id, path): content_hash for org_id, path, content_hash in existing}

    to_write = [r for r in rows if current_hash.get((r["org_id"], r["path"])) != r["content_hash"]]
    to_supersede = [(r["org_id"], r["path"]) for r in to_write if (r["org_id"], r["path"]) in current_hash]

    if to_supersede:
        await session.execute(
            update(OrgDatum)
            .where(tuple_(OrgDatum.org_id, OrgDatum.path).in_(to_supersede), OrgDatum.superseded_at.is_(None))
            .values(superseded_at=func.now())
        )
    if to_write:
        await session.execute(insert(OrgDatum).values(to_write))
    return len(to_write)


async def upsert_datum(
    session: AsyncSession,
    *,
    org_id: str,
    path: str,
    value: Any,
    source_url: str | None,
    retrieved_at: date | None = None,
    verification: str = "third_party_reported",
    quote: str | None = None,
    note: str | None = None,
    gap_reason: str | None = None,
    ingestion_run_id: Any = None,
) -> None:
    """Write one datum through the same supersede-on-change rule ingest_orgs uses in bulk.

    For a single out-of-band write - a re-researched fact outside a full ingestion run - not for
    batches: ingest_orgs builds many rows and writes them through _upsert_org_datum_rows directly
    in one pass instead of calling this per row.
    """
    retrieved_at_raw = retrieved_at.isoformat() if retrieved_at else None
    content_hash = _content_hash(value, source_url, retrieved_at_raw, verification, quote, note, gap_reason)
    value_type, extra = _value_type_and_extra({}, value)
    row = {
        "org_id": org_id,
        "path": path,
        "value": value,
        "value_type": value_type,
        "currency": extra.get("currency"),
        "fiscal_year": extra.get("fiscal_year"),
        "scope": extra.get("scope"),
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "quote": quote,
        "note": note,
        "verification": verification,
        "gap_reason": gap_reason,
        "content_hash": content_hash,
        "ingestion_run_id": ingestion_run_id,
    }
    await _upsert_org_datum_rows(session, [row])
    await session.commit()


# --- org_registration and org_warning: append-only via the content hash in their key -------------


def _registration_row(org_id: str, registration: dict[str, Any], run_id: Any) -> dict[str, Any]:
    identifier = registration.get("identifier")
    gap_reason = registration.get("gap_reason")
    note = registration.get("note")
    if identifier is None and gap_reason is None:
        gap_reason = derive_registration_gap_reason(registration)
    if identifier is None and not (note or "").strip():
        note = GENERATED_NOTE.get(gap_reason, GENERATED_NOTE["not_searched"])

    retrieved_at_raw = registration.get("retrieved_at")
    verification = registration.get("verification") or "unverified"
    status = registration.get("status")
    url = registration.get("url")

    content_hash = _content_hash(identifier, url, status, retrieved_at_raw, verification, note, gap_reason)

    return {
        "org_id": org_id,
        "registry": registration["registry"],
        "identifier": identifier,
        "url": url,
        "status": status,
        "retrieved_at": _parse_date(retrieved_at_raw),
        "verification": verification,
        "note": note,
        "gap_reason": gap_reason,
        "content_hash": content_hash,
        "ingestion_run_id": run_id,
    }


def _warning_row(org_id: str, warning: dict[str, Any], run_id: Any) -> dict[str, Any]:
    occurred_on_raw = warning.get("date")
    retrieved_at_raw = warning.get("retrieved_at")
    content_hash = _content_hash(
        warning.get("type"), warning.get("source_url"), occurred_on_raw, warning.get("note"), retrieved_at_raw
    )
    return {
        "org_id": org_id,
        "type": warning.get("type"),
        "source_url": warning.get("source_url"),
        "occurred_on": _parse_date(occurred_on_raw),
        "note": warning.get("note"),
        "retrieved_at": _parse_date(retrieved_at_raw),
        "content_hash": content_hash,
        "ingestion_run_id": run_id,
    }


async def _insert_ignore_conflicts(
    session: AsyncSession,
    model: type,
    rows: list[dict[str, Any]],
    index_elements: list[str],
) -> int:
    """A row with content identical to one already stored is a no-op; a row with new content is
    a new, distinct row - the model's own unique constraint (content_hash is part of the key)
    keeps history without needing a superseded_at flag. See core/models.py: OrgRegistration and
    OrgWarning."""
    if not rows:
        return 0
    statement = insert(model).values(rows).on_conflict_do_nothing(index_elements=index_elements).returning(model.id)
    result = await session.execute(statement)
    return len(result.scalars().all())


# --- org_alias -------------------------------------------------------------------------------


def _alias_candidates(org: dict[str, Any]) -> list[tuple[str, str]]:
    """(alias_norm, kind) pairs for one org: names.aliases[], names.common, and
    names.local_script.value when present. Deduped within the org first, so a name that is both
    the common name and also listed in aliases[] does not produce two candidate rows for the same
    org - local_script wins the kind if the same normalised form appears under both.
    """
    names = org["names"]
    candidates: dict[str, str] = {}
    for raw in names.get("aliases", []):
        norm = alias_norm(raw)
        if norm:
            candidates.setdefault(norm, "other")
    common_norm = alias_norm(names["common"])
    if common_norm:
        candidates.setdefault(common_norm, "other")
    local_script = names.get("local_script") or {}
    if local_script.get("value"):
        norm = alias_norm(local_script["value"])
        if norm:
            candidates[norm] = "local_script"
    return list(candidates.items())


def _partition_aliases(
    candidates: list[tuple[str, str, str]],
    existing: dict[str, str],
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
    """Split (alias_norm, org_id, kind) candidates into rows to insert and collisions to log.

    A collision is the same alias_norm claimed by two DIFFERENT org_ids, either against what is
    already in the database or between two orgs in this same batch. The same org re-asserting an
    alias it already owns is the idempotent case, not a collision: nothing to insert, nothing to
    log. alias_norm is globally unique (core.models.OrgAlias.uq_org_alias_norm), so a genuine
    collision is a research question about which org actually owns that name, not something a
    loader should silently resolve.
    """
    owner = dict(existing)
    rows: list[dict[str, Any]] = []
    collisions: list[tuple[str, str, str]] = []
    for norm, org_id, kind in candidates:
        current_owner = owner.get(norm)
        if current_owner is None:
            owner[norm] = org_id
            rows.append({"alias_norm": norm, "org_id": org_id, "kind": kind})
        elif current_owner != org_id:
            collisions.append((norm, current_owner, org_id))
    return rows, collisions


# --- the job -----------------------------------------------------------------------------------


async def ingest_orgs(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
) -> None:
    """Idempotent. Loads the deduplicated 44-organisation pilot dataset and upserts
    organisations, org_datum, org_alias, org_registration and org_warning."""
    if handle is None:
        async with run_context(session_factory, "ingest_orgs") as run:
            await ingest_orgs(session_factory, run)
        return

    orgs = load_orgs()
    run_id = handle.id

    org_rows = [_organisation_row(org, run_id) for org in orgs]

    datum_rows: list[dict[str, Any]] = []
    for org in orgs:
        gaps = {normalise_path(g) for g in org.get("data_gaps", [])}
        for path, datum in walk_datums(org):
            datum_rows.append(_datum_row(org["org_id"], path, datum, gaps, run_id))

    registration_rows = [
        _registration_row(org["org_id"], registration, run_id)
        for org in orgs
        for registration in org.get("registrations", [])
    ]
    warning_rows = [_warning_row(org["org_id"], warning, run_id) for org in orgs for warning in org.get("warnings", [])]
    alias_candidates = [(norm, org["org_id"], kind) for org in orgs for norm, kind in _alias_candidates(org)]

    written = 0
    skipped = 0
    collisions: list[tuple[str, str, str]] = []

    async with session_factory() as session:
        org_written = await _upsert(session, Organisation, org_rows, "org_id", ORG_COLUMNS)
        written += org_written
        skipped += len(org_rows) - org_written

        datum_written = await _upsert_org_datum_rows(session, datum_rows)
        written += datum_written
        skipped += len(datum_rows) - datum_written

        reg_written = await _insert_ignore_conflicts(
            session, OrgRegistration, registration_rows, ["org_id", "registry", "content_hash"]
        )
        written += reg_written
        skipped += len(registration_rows) - reg_written

        warn_written = await _insert_ignore_conflicts(session, OrgWarning, warning_rows, ["org_id", "content_hash"])
        written += warn_written
        skipped += len(warning_rows) - warn_written

        alias_norms = {c[0] for c in alias_candidates}
        existing_aliases: dict[str, str] = {}
        if alias_norms:
            statement = select(OrgAlias.alias_norm, OrgAlias.org_id).where(OrgAlias.alias_norm.in_(alias_norms))
            rows = await session.execute(statement)
            existing_aliases = dict(rows.all())
        alias_rows, collisions = _partition_aliases(alias_candidates, existing_aliases)
        for norm, existing_org_id, new_org_id in collisions:
            log.warning(
                "org_alias_collision",
                extra={"alias_norm": norm, "existing_org_id": existing_org_id, "new_org_id": new_org_id},
            )
        alias_written = await _insert_ignore_conflicts(session, OrgAlias, alias_rows, ["alias_norm"])
        written += alias_written
        skipped += len(alias_candidates) - alias_written

        await session.commit()

    handle.count(written=written, skipped=skipped)
    log.info(
        "ingest_orgs_done",
        extra={
            "orgs": len(org_rows),
            "datums": len(datum_rows),
            "registrations": len(registration_rows),
            "warnings": len(warning_rows),
            "aliases": len(alias_candidates),
            "alias_collisions": len(collisions),
            "written": written,
            "skipped": skipped,
        },
    )
