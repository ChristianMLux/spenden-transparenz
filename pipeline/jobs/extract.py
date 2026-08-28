"""extract_statements: turn report bodies into gated response_statement rows.

Hot path: one LLM call per report (I/O), never one call per claim - claims do not exist until
after the call returns. The loop is bounded twice over: at most MAX_REPORTS_PER_RUN reports, and
the loop stops as soon as the accumulated spend already meets or exceeds MAX_RUN_COST_USD, so a
run's cost is bounded by construction rather than by hoping the model behaves. Reports are selected
with one query (not one query per candidate), and known-district context is looked up once per
disaster present in the batch (not once per report).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from core import enums
from core.logging import get_logger
from core.models import District, Report, ResponseStatement, StatementDistrict
from core.settings import get_settings
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.extract import client as llm_client
from pipeline.extract.prompt import PROMPT_VERSION, ReportInput
from pipeline.extract.validate import MAX_QUOTE_WORDS, gate, word_count
from pipeline.runs import RunHandle, run_context

log = get_logger("extract_statements")

# A report that has failed extraction this many times is excluded permanently rather than retried
# forever on every run - a persistently malformed body or a persistently failing call should not
# burn budget on every single cron tick.
MAX_ATTEMPTS = 3

# Columns extract_statements owns and may update on a re-run. org_id is deliberately absent: it
# belongs to match_orgs, and including it here would let a re-extraction silently erase a match
# that ran after the original extraction. ingestion_run_id is also absent from this list on
# purpose - see _upsert_statements.
_UPSERT_COLUMNS = (
    "org_name_raw",
    "activity",
    "activity_type",
    "where_raw",
    "happened_on",
    "amount",
    "currency",
    "amount_basis",
    "quote",
    "quote_offset",
    "confidence",
    "verification",
    "model",
    "prompt_version",
    "status",
)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_amount(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _safe_enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    """A model that ignores the tool schema's enum must not crash the whole batch write; it falls
    back to the safest catch-all value instead."""
    return value if value in allowed else default


def content_hash(claim: dict[str, Any]) -> str:
    """Identity of an extracted claim's content, independent of its gate verdict.

    Keeping status out of the hash means a claim that is re-extracted identically but with a
    different gate verdict (for example after a bug fix in validate.py) updates the existing row
    instead of creating a duplicate beside it.
    """
    payload = {
        "org_name_raw": claim.get("org_name_raw"),
        "activity": claim.get("activity"),
        "activity_type": claim.get("activity_type"),
        "where_raw": sorted(claim.get("where_raw") or []),
        "happened_on": claim.get("happened_on"),
        "amount": str(claim["amount"]) if claim.get("amount") is not None else None,
        "currency": claim.get("currency"),
        "amount_basis": claim.get("amount_basis"),
        "quote": claim.get("quote"),
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_row(report_id: int, claim: dict[str, Any], status: str, run_id: UUID, model: str) -> dict[str, Any] | None:
    quote = (claim.get("quote") or "").strip()
    org_name_raw = (claim.get("org_name_raw") or "").strip()
    activity = (claim.get("activity") or "").strip()
    if not quote or not org_name_raw or not activity:
        # The schema marks these required; a model that skips one anyway has produced a claim with
        # nothing to display or verify, so it is dropped rather than stored with a blank field.
        return None

    if word_count(quote) > MAX_QUOTE_WORDS:
        # ck_response_statement_quote_words forbids this on EVERY row, whatever its status, so the
        # row gate() hands back for an over-long quote is one the table refuses. A live run lost a
        # whole batch to that on a 55-word French sentence. The claim is dropped here, where it can
        # still be counted, rather than at the INSERT, where it can only abort.
        return None

    return {
        "report_id": report_id,
        "org_name_raw": org_name_raw,
        "activity": activity,
        "activity_type": _safe_enum(claim.get("activity_type"), enums.ACTIVITY_TYPE, "other"),
        "where_raw": list(claim.get("where_raw") or []),
        "happened_on": _parse_date(claim.get("happened_on")),
        "amount": claim.get("amount"),
        "currency": claim.get("currency"),
        "amount_basis": _safe_enum(claim.get("amount_basis"), enums.AMOUNT_BASIS, "reported"),
        "quote": quote,
        "quote_offset": claim.get("quote_offset"),
        "confidence": None,
        "verification": "third_party_reported",
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "status": status,
        "content_hash": content_hash(claim),
        "ingestion_run_id": run_id,
    }


@dataclass(frozen=True)
class _Candidate:
    """One report's data as plain values, detached from the session.

    Deliberately not the ORM object. This loop makes a twenty-second network call between database
    touches and has to survive a rolled-back write, and a rollback expires every ORM object in the
    session - after which reading even `report.id` for a log line emits a SELECT from a synchronous
    context and raises MissingGreenlet. A live run ended that way two reports after a refused
    write, having already paid for both calls. Plain values cannot expire.
    """

    id: int
    url: str
    title: str | None
    body_text: str
    published_at: datetime | None
    disaster_glide_id: str | None


async def _select_candidate_reports(session: AsyncSession, limit: int) -> list[_Candidate]:
    """Reports with a body, under the attempt cap, not already extracted at this prompt_version.

    One query. The cache key is effectively (body_sha256, prompt_version): a report's body_sha256
    is set once when it is fetched and never rewritten (fetch_report_bodies only fills reports
    that have none yet), so "already has a response_statement at the current prompt_version" and
    "already extracted this body under this prompt_version" are the same condition here.
    """
    already_extracted = select(ResponseStatement.report_id).where(ResponseStatement.prompt_version == PROMPT_VERSION)
    stmt = (
        select(
            Report.id,
            Report.url,
            Report.title,
            Report.body_text,
            Report.published_at,
            Report.disaster_glide_id,
        )
        .where(Report.body_text.is_not(None))
        .where(Report.extraction_attempts < MAX_ATTEMPTS)
        .where(Report.id.not_in(already_extracted))
        .order_by(Report.id)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_Candidate(*row) for row in result.all()]


async def _known_districts_by_disaster(session: AsyncSession, glide_ids: set[str]) -> dict[str, tuple[str, ...]]:
    """Districts already resolved for other statements on the same disaster, one query for every
    disaster in the batch - not one query per report."""
    glide_ids = {g for g in glide_ids if g}
    if not glide_ids:
        return {}
    stmt = (
        select(Report.disaster_glide_id, District.name)
        .join(ResponseStatement, ResponseStatement.report_id == Report.id)
        .join(StatementDistrict, StatementDistrict.statement_id == ResponseStatement.id)
        .join(District, District.code == StatementDistrict.district_code)
        .where(Report.disaster_glide_id.in_(glide_ids))
        .distinct()
    )
    result = await session.execute(stmt)
    grouped: dict[str, set[str]] = {}
    for glide_id, name in result.all():
        grouped.setdefault(glide_id, set()).add(name)
    return {glide_id: tuple(sorted(names)) for glide_id, names in grouped.items()}


async def _upsert_statements(session: AsyncSession, rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    """One statement for the whole report's claims. Returns (written, skipped, rejected).

    ingestion_run_id is written on INSERT but is excluded from both the SET clause and the
    "changed" comparison: it is a fresh UUID on every run, so including it in either would make
    every re-run look like a change and break the "second run writes zero rows" contract.
    """
    if not rows:
        return 0, 0, 0
    statement = insert(ResponseStatement).values(rows)
    changed = or_(
        *[getattr(ResponseStatement, col).is_distinct_from(statement.excluded[col]) for col in _UPSERT_COLUMNS]
    )
    statement = statement.on_conflict_do_update(
        index_elements=["report_id", "content_hash"],
        set_={col: statement.excluded[col] for col in _UPSERT_COLUMNS},
        where=changed,
    ).returning(ResponseStatement.id, ResponseStatement.status)
    result = await session.execute(statement)
    written = 0
    rejected = 0
    for _row_id, status in result.all():
        if status == "rejected_unverbatim":
            rejected += 1
        else:
            written += 1
    skipped = len(rows) - written - rejected
    return written, skipped, rejected


async def extract_statements(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
    *,
    max_reports: int | None = None,
    max_cost_usd: Decimal | float | None = None,
) -> None:
    """Extract response statements from report bodies, gated by count, cost, attempts and cache."""
    if handle is None:
        async with run_context(session_factory, "extract_statements") as run:
            await extract_statements(session_factory, run, max_reports=max_reports, max_cost_usd=max_cost_usd)
        return

    settings = get_settings()
    report_limit = max_reports if max_reports is not None else settings.max_reports_per_run
    cost_cap = Decimal(str(max_cost_usd)) if max_cost_usd is not None else Decimal(str(settings.max_run_cost_usd))

    async with session_factory() as session:
        reports = await _select_candidate_reports(session, report_limit)
        known_by_disaster = await _known_districts_by_disaster(
            session, {r.disaster_glide_id for r in reports if r.disaster_glide_id}
        )

        for processed, report in enumerate(reports):
            if handle.cost_usd >= cost_cap:
                log.info(
                    "extract_statements_cost_cap_reached",
                    extra={"cost_usd": str(handle.cost_usd), "cap_usd": str(cost_cap), "reports_processed": processed},
                )
                break

            # Incremented before the call, not after: a crash on the line below must still leave
            # this attempt counted, or a permanently-failing report retries on every run forever.
            # An explicit UPDATE rather than a mutated ORM attribute, so this loop holds no
            # session-bound object that a later rollback could expire underneath it.
            await session.execute(
                update(Report).where(Report.id == report.id).values(extraction_attempts=Report.extraction_attempts + 1)
            )
            await session.commit()

            report_input = ReportInput(
                url=report.url,
                title=report.title or "",
                body=report.body_text,
                published_at=report.published_at.date().isoformat() if report.published_at else None,
                known_districts=known_by_disaster.get(report.disaster_glide_id or "", ()),
            )

            result = await llm_client.extract(report_input)
            handle.spend(cost_usd=result.cost_usd, tokens_in=result.tokens_in, tokens_out=result.tokens_out)
            log.info(
                "extract_statements_report_extracted",
                extra={
                    "report_id": report.id,
                    "claims": len(result.claims),
                    "cost_usd": str(result.cost_usd),
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                },
            )

            rows = []
            dropped = 0
            for claim in result.claims:
                status, gated_claim = gate(claim, report.body_text)
                row = _build_row(report.id, gated_claim, status, handle.id, settings.llm_model)
                if row is None:
                    # _build_row's own guard, not gate()'s: a claim missing quote, org_name_raw or
                    # activity never becomes a row at all, so without counting it here it is
                    # invisible to the rejection rate - a model that starts omitting required
                    # fields would look identical to a model producing nothing but clean claims.
                    dropped += 1
                    log.info(
                        "extract_statements_claim_dropped",
                        extra={"report_id": report.id, "reason": "unusable field, or a quote the table cannot store"},
                    )
                    continue
                rows.append(row)

            if rows:
                try:
                    written, skipped, rejected = await _upsert_statements(session, rows)
                    await session.commit()
                except SQLAlchemyError:
                    # A run pays for its LLM calls before it writes anything, so letting one
                    # refused write end the run throws away every report after it and the money
                    # already spent on them. The report is rolled back and its claims counted as
                    # rejected instead - which is what keeps this honest, because a systematic
                    # write failure cannot hide behind a "succeeded" run: every claim it loses
                    # lands in the rejected total the malformed rate is measured against.
                    await session.rollback()
                    log.exception(
                        "extract_statements_write_refused",
                        extra={"report_id": report.id, "claims": len(rows)},
                    )
                    handle.count(rejected=len(rows) + dropped)
                else:
                    handle.count(written=written, skipped=skipped, rejected=rejected + dropped)
            elif dropped:
                handle.count(rejected=dropped)
            else:
                handle.count(skipped=1)
