"""Load the reference data every other job and every filter depends on.

Districts come from the HAPI common operational dataset (77 Nepali admin2 units, codes like
NP0301), sources from data/sources-catalog.json with their licences.

Two bulk statements, not 87 round trips: the whole job is two INSERT ... ON CONFLICT DO UPDATE
statements with a WHERE that skips rows whose content is unchanged. That WHERE is what makes the
"second run writes zero rows" contract checkable - without it Postgres rewrites every row on every
run and an upsert that does nothing looks identical to one that rewrites everything.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from core.logging import get_logger
from core.models import District, Source
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.runs import RunHandle, run_context

log = get_logger("seed_reference")

REPO = Path(__file__).resolve().parents[2]
ADMIN2 = REPO / "data" / "raw" / "hapi" / "admin2_NPL.json"
CATALOG = REPO / "data" / "sources-catalog.json"

DISTRICT_SOURCE_ID = "hdx_hapi"

SOURCE_COLUMNS = ("name", "url", "licence", "licence_url", "licence_note", "default_verification", "retrieved_at")
DISTRICT_COLUMNS = ("name", "admin1_code", "admin1_name", "source_id")


def read_districts() -> list[dict[str, Any]]:
    payload = json.loads(ADMIN2.read_text(encoding="utf-8"))
    rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    return [
        {
            "code": row["code"],
            "name": row["name"],
            "admin1_code": row["admin1_code"],
            "admin1_name": row["admin1_name"],
            "source_id": DISTRICT_SOURCE_ID,
        }
        for row in rows
    ]


def read_sources() -> list[dict[str, Any]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "url": row["url"] or "",
            "licence": row["licence"],
            "licence_url": row["licence_url"],
            "licence_note": row["licence_note"],
            "default_verification": row["default_verification"],
            # asyncpg binds DATE parameters as datetime.date, not as an ISO string. Parsing here
            # rather than at the database boundary also means a malformed date in the catalogue
            # fails when the file is read, not halfway through a write.
            "retrieved_at": date.fromisoformat(row["retrieved_at"]) if row.get("retrieved_at") else None,
        }
        for row in payload["sources"]
    ]


async def _upsert(
    session: AsyncSession,
    model: type,
    rows: list[dict[str, Any]],
    key: str,
    columns: tuple[str, ...],
) -> int:
    """One statement for the whole batch. Returns the number of rows that actually changed.

    The WHERE on DO UPDATE is the point: is_distinct_from treats NULLs correctly, so a row whose
    every column already matches is not rewritten and does not come back in RETURNING.
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


async def seed_reference(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
) -> None:
    """Idempotent. Sources first: districts reference them."""
    if handle is None:
        async with run_context(session_factory, "seed_reference") as run:
            await seed_reference(session_factory, run)
        return

    sources = read_sources()
    districts = read_districts()

    async with session_factory() as session:
        written_sources = await _upsert(session, Source, sources, "id", SOURCE_COLUMNS)
        written_districts = await _upsert(session, District, districts, "code", DISTRICT_COLUMNS)
        await session.commit()

    total = len(sources) + len(districts)
    written = written_sources + written_districts
    handle.count(written=written, skipped=total - written)
    log.info(
        "seed_reference_done",
        extra={"sources": len(sources), "districts": len(districts), "written": written, "skipped": total - written},
    )
