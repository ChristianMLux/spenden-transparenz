"""resolve_districts: where_raw[] -> district_alias -> statement_district.

Two resolutions, and the distinction survives to the API because they are different claims:
"stated" - the statement's own where_raw names a place that resolves via district_alias.
"inherited_from_report" - the statement names no place, so it inherits the union of districts
already stated by sibling statements on the same report.

district_alias is already seeded by seed_reference (160 rows: 77 district names, 77 "<name>
district" forms, 6 settlement variants) and seed_reference.UNRESOLVABLE lists the phrases that must
resolve to no district at all. This job consumes both and adds neither: a phrase not in
district_alias simply fails the lookup and produces no row, which is exactly what an unresolvable
phrase like a river corridor or "Nepal" should do - inventing a single district for it would be a
guess this product exists not to make.

Known limitation, not silently hidden: this job never deletes rows (the platform-wide idempotency
contract). If a statement is inherited_from_report on one run because its place name did not yet
have an alias, and a later run adds that alias so the same statement now resolves directly, the new
"stated" row is added correctly, but a pre-existing inherited row for a *different* district code
stays in the table rather than being removed. Cleaning that up needs a deliberate follow-up (a
migration or a targeted re-run after truncating statement_district), not a silent delete inside this
job.

Hot path: one query for all district aliases, one query for all candidate statements' where_raw,
and one batched upsert for every resulting row - no query inside the per-statement loop.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from core.logging import get_logger
from core.models import Disaster, DistrictAlias, ResponseStatement, StatementDistrict
from core.normalise import alias_norm
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.revalidate import crisis_tag, revalidate
from pipeline.runs import RunHandle, run_context

log = get_logger("resolve_districts")


async def _alias_map(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(DistrictAlias.alias_norm, DistrictAlias.district_code))
    return dict(result.all())


async def _existing_statement_districts(session: AsyncSession) -> dict[int, dict[str, str]]:
    """statement_id -> {district_code: resolution} for every row already written."""
    result = await session.execute(
        select(StatementDistrict.statement_id, StatementDistrict.district_code, StatementDistrict.resolution)
    )
    by_statement: dict[int, dict[str, str]] = defaultdict(dict)
    for statement_id, code, resolution in result.all():
        by_statement[statement_id][code] = resolution
    return by_statement


async def _upsert_statement_districts(session: AsyncSession, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """One statement for every row this run wants to write. Returns (written, skipped)."""
    if not rows:
        return 0, 0
    statement = insert(StatementDistrict).values(rows)
    changed = StatementDistrict.resolution.is_distinct_from(statement.excluded.resolution)
    statement = statement.on_conflict_do_update(
        index_elements=["statement_id", "district_code"],
        set_={"resolution": statement.excluded.resolution},
        where=changed,
    ).returning(StatementDistrict.statement_id)
    result = await session.execute(statement)
    written = len(result.scalars().all())
    return written, len(rows) - written


async def resolve_districts(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
) -> None:
    """Resolve where_raw to district_code for every non-rejected statement. Idempotent."""
    if handle is None:
        async with run_context(session_factory, "resolve_districts") as run:
            await resolve_districts(session_factory, run)
        return

    async with session_factory() as session:
        aliases = await _alias_map(session)
        existing = await _existing_statement_districts(session)

        candidates = (
            await session.execute(
                select(ResponseStatement.id, ResponseStatement.report_id, ResponseStatement.where_raw).where(
                    ResponseStatement.status != "rejected_unverbatim"
                )
            )
        ).all()

        # Pass 1: resolve each statement's own where_raw. Also build, per report, the union of
        # codes its statements stated directly - the fallback pool for statements that named no
        # place at all.
        stated_codes: dict[int, set[str]] = {}
        needs_fallback: dict[int, list[int]] = defaultdict(list)
        report_stated_union: dict[int, set[str]] = defaultdict(set)

        for statement_id, report_id, where_raw in candidates:
            codes = {aliases[key] for raw in (where_raw or []) if (key := alias_norm(raw)) in aliases}
            if codes:
                stated_codes[statement_id] = codes
                report_stated_union[report_id] |= codes
            else:
                needs_fallback[report_id].append(statement_id)

        rows: list[dict[str, Any]] = []
        for statement_id, codes in stated_codes.items():
            for code in codes:
                rows.append({"statement_id": statement_id, "district_code": code, "resolution": "stated"})

        # Pass 2: statements that named no place inherit the report's stated union - unless they
        # already carry a genuine "stated" row from an earlier run (see the module docstring on
        # why a stale inherited row cannot simply be deleted once that happens).
        for report_id, statement_ids in needs_fallback.items():
            inherited_codes = report_stated_union.get(report_id, set())
            for statement_id in statement_ids:
                if any(res == "stated" for res in existing.get(statement_id, {}).values()):
                    continue
                for code in inherited_codes:
                    rows.append(
                        {"statement_id": statement_id, "district_code": code, "resolution": "inherited_from_report"}
                    )

        written, skipped = await _upsert_statement_districts(session, rows)
        await session.commit()

        handle.count(written=written, skipped=skipped)
        log.info(
            "resolve_districts_done",
            extra={
                "statements_considered": len(candidates),
                "rows_written": written,
                "rows_skipped": skipped,
            },
        )

    # After the commit, never before: a cache hint is not data, and a web app that is down must
    # not turn a successful ingestion into a failed one.
    if written:
        await _revalidate_crises(session_factory)


async def _revalidate_crises(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Ask the web app to re-render every active crisis board. Best-effort, never raises."""
    async with session_factory() as session:
        glide_ids = (
            (await session.execute(select(Disaster.glide_id).where(Disaster.is_active.is_(True)))).scalars().all()
        )
    revalidate([crisis_tag(glide_id) for glide_id in glide_ids])
