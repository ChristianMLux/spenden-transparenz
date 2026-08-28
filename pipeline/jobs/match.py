"""match_orgs: org_name_raw -> core.normalise.alias_norm -> org_alias.org_id.

Exact normalised match only. No fuzzy matching in v1 - a wrong organisation attributed to a relief
activity is worse than a null one, and org_id IS NULL is a designed, visible state meaning "named
but not identified", not a gap to paper over with a similarity score. Unmatched names are logged
with their counts so aliases can be added deliberately, one line per name, never guessed.

Separate job from extract_statements on purpose: a new alias can re-match every existing statement
without paying for a single LLM call.

Hot path: one alias lookup per statement against an in-memory dict built from a single query - no
query inside the loop. Every changed row is written with one batched UPDATE (SQLAlchemy's
executemany-style bulk update via bindparam), not one UPDATE per statement.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from core.logging import get_logger
from core.models import OrgAlias, ResponseStatement
from core.normalise import alias_norm
from sqlalchemy import bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.runs import RunHandle, run_context

log = get_logger("match_orgs")

# Built against __table__ (Core), not the mapped class: an ORM-level update(ResponseStatement)
# whose WHERE matches the primary key routes through SQLAlchemy's "bulk UPDATE by primary key"
# path, which demands the primary-key column's own name ("id") as the parameter key and rejects
# a custom bindparam name. Going through the Core Table object is a plain SQL UPDATE with
# executemany semantics - one prepared statement, one parameter set per changed row - with no ORM
# unit-of-work synchronization to opt out of, which is also correct here: match_orgs never holds
# these ResponseStatement rows as loaded ORM objects in this session.
_UPDATE_STATEMENT = (
    update(ResponseStatement.__table__)
    .where(ResponseStatement.__table__.c.id == bindparam("stmt_id"))
    .values(org_id=bindparam("new_org_id"))
)


async def _alias_map(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(OrgAlias.alias_norm, OrgAlias.org_id))
    return dict(result.all())


async def match_orgs(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
) -> None:
    """Resolve org_name_raw to org_id wherever an exact alias exists. Idempotent, never clears an
    existing match."""
    if handle is None:
        async with run_context(session_factory, "match_orgs") as run:
            await match_orgs(session_factory, run)
        return

    async with session_factory() as session:
        aliases = await _alias_map(session)

        candidates = (
            await session.execute(
                select(ResponseStatement.id, ResponseStatement.org_name_raw, ResponseStatement.org_id).where(
                    ResponseStatement.status != "rejected_unverbatim"
                )
            )
        ).all()

        updates: list[dict[str, Any]] = []
        unmatched: Counter[str] = Counter()
        skipped = 0

        for statement_id, org_name_raw, current_org_id in candidates:
            org_id = aliases.get(alias_norm(org_name_raw))
            if org_id is None:
                unmatched[org_name_raw] += 1
                skipped += 1
            elif org_id == current_org_id:
                skipped += 1
            else:
                # Never clears an existing match: a name that stops matching is a research
                # question (was an alias removed?), not evidence the earlier match was wrong.
                updates.append({"stmt_id": statement_id, "new_org_id": org_id})

        if updates:
            await session.execute(_UPDATE_STATEMENT, updates)
        await session.commit()

        handle.count(written=len(updates), skipped=skipped)
        for org_name_raw, count in sorted(unmatched.items(), key=lambda kv: (-kv[1], kv[0])):
            log.info("match_orgs_unmatched", extra={"org_name_raw": org_name_raw, "count": count})
        log.info(
            "match_orgs_done",
            extra={"matched": len(updates), "skipped": skipped, "unmatched_names": len(unmatched)},
        )
