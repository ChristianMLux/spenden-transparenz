"""GET /v1/disasters, GET /v1/disasters/{glide_id}.

Small, rarely-changing reference data: the crises this deployment has a response board for.
"""

from __future__ import annotations

from typing import Annotated

from app.deps import get_session, list_cache
from app.schemas import DisasterOut
from core.models import Disaster
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/disasters", tags=["disasters"])


def _out(row: Disaster) -> DisasterOut:
    return DisasterOut(
        glide_id=row.glide_id,
        reliefweb_id=row.reliefweb_id,
        name=row.name,
        country_iso3=row.country_iso3,
        started_on=row.started_on,
        is_active=row.is_active,
        source_url=row.source_url,
    )


@router.get(
    "",
    response_model=list[DisasterOut],
    summary="Crises with a response board.",
    dependencies=[Depends(list_cache)],
)
async def list_disasters(session: Annotated[AsyncSession, Depends(get_session)]) -> list[DisasterOut]:
    rows = (await session.execute(select(Disaster).order_by(Disaster.started_on.desc()))).scalars().all()
    return [_out(row) for row in rows]


@router.get(
    "/{glide_id}",
    response_model=DisasterOut,
    summary="One crisis by its GLIDE id.",
    dependencies=[Depends(list_cache)],
)
async def get_disaster(
    session: Annotated[AsyncSession, Depends(get_session)],
    glide_id: Annotated[str, Path(examples=["ff-2026-000162-npl"])],
) -> DisasterOut:
    row = await session.get(Disaster, glide_id)
    if row is None:
        raise HTTPException(status_code=404, detail="disaster not found")
    return _out(row)
