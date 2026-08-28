"""Reference data: districts, sources, enums, freshness.

Everything here changes rarely (districts and sources are seeded once; enums are code) or is
cheap to compute (freshness is one grouped query over ingestion_run), so it all gets the longest
cache tier.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from app.deps import get_session, meta_cache
from app.schemas import DistrictOut, EnumsOut, FreshnessEntry, FreshnessOut, SourceOut
from core import enums
from core.models import District, IngestionRun, Source
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/meta", tags=["meta"])


@router.get(
    "/districts",
    response_model=list[DistrictOut],
    summary="The 77 Nepali districts.",
    dependencies=[Depends(meta_cache)],
)
async def list_districts(session: Annotated[AsyncSession, Depends(get_session)]) -> list[DistrictOut]:
    rows = (await session.execute(select(District).order_by(District.code))).scalars().all()
    return [
        DistrictOut(code=row.code, name=row.name, admin1_code=row.admin1_code, admin1_name=row.admin1_name)
        for row in rows
    ]


@router.get(
    "/sources",
    response_model=list[SourceOut],
    summary="Sources with their licences.",
    dependencies=[Depends(meta_cache)],
)
async def list_sources(session: Annotated[AsyncSession, Depends(get_session)]) -> list[SourceOut]:
    rows = (await session.execute(select(Source).order_by(Source.id))).scalars().all()
    return [
        SourceOut(
            id=row.id,
            name=row.name,
            url=row.url,
            licence=row.licence,
            licence_url=row.licence_url,
            licence_note=row.licence_note,
            default_verification=row.default_verification,
            retrieved_at=row.retrieved_at,
        )
        for row in rows
    ]


@router.get(
    "/enums",
    response_model=EnumsOut,
    summary="Enum values, so the frontend hardcodes none.",
    dependencies=[Depends(meta_cache)],
)
async def get_enums() -> EnumsOut:
    return EnumsOut(enums={name: list(values) for name, values in enums.ALL_ENUMS.items()})


@router.get(
    "/freshness",
    response_model=FreshnessOut,
    summary="When each job last succeeded.",
    dependencies=[Depends(meta_cache)],
)
async def get_freshness(session: Annotated[AsyncSession, Depends(get_session)]) -> FreshnessOut:
    # The latest successful run per job, in one query: a per-job max(started_at) subquery joined
    # back to the row that produced it. No loop over jobs, no N+1.
    latest = (
        select(IngestionRun.job, func.max(IngestionRun.started_at).label("started_at"))
        .where(IngestionRun.status == "succeeded")
        .group_by(IngestionRun.job)
        .subquery()
    )
    rows = (
        await session.execute(
            select(IngestionRun.job, IngestionRun.finished_at, IngestionRun.rows_written).join(
                latest,
                (IngestionRun.job == latest.c.job) & (IngestionRun.started_at == latest.c.started_at),
            )
        )
    ).all()
    jobs = [FreshnessEntry(job=row.job, last_success_at=row.finished_at, rows_written=row.rows_written) for row in rows]
    return FreshnessOut(generated_at=datetime.now(UTC), jobs=jobs)
