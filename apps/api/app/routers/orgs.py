"""GET /v1/orgs, GET /v1/orgs/{org_id}, GET /v1/orgs/{org_id}/history.

The detail route is the one place every datum for an organisation is served together, gaps
included: `data` never drops a path just because its value is null, and `data_gaps` names every
one of them so a frontend can render "what we don't know" without walking the whole dict.
"""

from __future__ import annotations

from typing import Annotated, Literal

from app.deps import ILIKE_ESCAPE, detail_cache, get_session, ilike_pattern, list_cache
from app.routers.statements import hydrate_statements, statement_query
from app.schemas import (
    DatumHistoryEntry,
    OrgDetail,
    RegistrationOut,
    WarningOut,
    serialise_datum,
)
from core.models import OrgAlias, Organisation, OrgDatum, OrgRegistration, OrgWarning, ResponseStatement
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/orgs", tags=["organisations"])

# Same closed vocabulary as the Phase 0 stub - a plain regex-pattern string here would change the
# OpenAPI shape (and the TypeScript union type the web team already generated) from an enum to an
# unconstrained pattern-matched string.
Sort = Literal["latest", "name", "least_data"]
Hq = Literal["local", "international"]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]
OffsetQuery = Annotated[int, Query(ge=0)]
SearchQuery = Annotated[str | None, Query(max_length=80, description="name search, matched case-insensitively")]
OrgTypeQuery = Annotated[list[str], Query(description="repeatable")]


CURRENT_VALUE = (OrgDatum.superseded_at.is_(None)) & (OrgDatum.value.isnot(None))


def _org_detail_base(row: Organisation) -> dict:
    return {
        "org_id": row.org_id,
        "name_common": row.name_common,
        "org_type": row.org_type,
        "hq_country": row.hq_country,
        "hq_city": row.hq_city,
        "website": row.website,
        "last_updated": row.last_updated,
        "research_notes": row.research_notes,
    }


@router.get("", response_model=list[OrgDetail], summary="Organisations.", dependencies=[Depends(list_cache)])
async def list_orgs(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    org_type: OrgTypeQuery = [],  # noqa: B006 - FastAPI reads the default to build the schema
    hq: Hq | None = None,
    q: SearchQuery = None,
    sort: Sort = "name",
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[OrgDetail]:
    value_count = (
        select(func.count(OrgDatum.id))
        .where(OrgDatum.org_id == Organisation.org_id, CURRENT_VALUE)
        .correlate(Organisation)
        .scalar_subquery()
    )
    query = select(Organisation, value_count.label("value_count"))
    if org_type:
        query = query.where(Organisation.org_type.in_(org_type))
    if hq == "local":
        query = query.where(Organisation.hq_country == "NP")
    elif hq == "international":
        query = query.where(Organisation.hq_country.isnot(None), Organisation.hq_country != "NP")
    if q:
        query = query.where(Organisation.name_common.ilike(ilike_pattern(q), escape=ILIKE_ESCAPE))

    if sort == "latest":
        query = query.order_by(Organisation.last_updated.desc().nullslast(), Organisation.org_id)
    elif sort == "least_data":
        # A count of how many datum paths carry a value, ascending - a fact about our coverage of
        # the organisation, never a judgement about the organisation. Never offered as "verification".
        query = query.order_by("value_count", Organisation.org_id)
    else:
        query = query.order_by(Organisation.name_common)

    rows = (await session.execute(query)).all()
    response.headers["X-Total-Count"] = str(len(rows))
    page = rows[offset : offset + limit]

    return [await _detail(session, row.Organisation, with_statements=False) for row in page]


async def _detail(session: AsyncSession, org: Organisation, *, with_statements: bool) -> OrgDetail:
    aliases = (await session.execute(select(OrgAlias.alias_norm).where(OrgAlias.org_id == org.org_id))).scalars().all()
    registrations = (
        (await session.execute(select(OrgRegistration).where(OrgRegistration.org_id == org.org_id))).scalars().all()
    )
    warnings = (await session.execute(select(OrgWarning).where(OrgWarning.org_id == org.org_id))).scalars().all()
    datums = (
        (await session.execute(select(OrgDatum).where(OrgDatum.org_id == org.org_id, OrgDatum.superseded_at.is_(None))))
        .scalars()
        .all()
    )

    statements = []
    if with_statements:
        query = statement_query(org_id=org.org_id).order_by(
            ResponseStatement.happened_on.desc().nullslast(), ResponseStatement.created_at.desc()
        )
        pairs = [(row.ResponseStatement, row.Report) for row in (await session.execute(query)).all()]
        statements = await hydrate_statements(session, pairs)

    data = {row.path: serialise_datum(row) for row in datums}
    data_gaps = sorted(path for path, datum in data.items() if datum.is_gap)

    return OrgDetail(
        **_org_detail_base(org),
        aliases=aliases,
        registrations=[
            RegistrationOut(
                registry=r.registry,
                identifier=r.identifier,
                url=r.url,
                status=r.status,
                retrieved_at=r.retrieved_at,
                verification=r.verification,
                note=r.note,
                gap_reason=r.gap_reason,
            )
            for r in registrations
        ],
        warnings=[
            WarningOut(
                type=w.type,
                source_url=w.source_url,
                occurred_on=w.occurred_on,
                note=w.note,
                retrieved_at=w.retrieved_at,
            )
            for w in warnings
        ],
        statements=statements,
        data=data,
        data_gaps=data_gaps,
    )


@router.get(
    "/{org_id}",
    response_model=OrgDetail,
    summary="One organisation, gaps included.",
    dependencies=[Depends(detail_cache)],
)
async def get_org(session: Annotated[AsyncSession, Depends(get_session)], org_id: str) -> OrgDetail:
    org = await session.get(Organisation, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organisation not found")
    return await _detail(session, org, with_statements=True)


@router.get(
    "/{org_id}/history",
    response_model=list[DatumHistoryEntry],
    summary="How one value changed.",
    dependencies=[Depends(detail_cache)],
)
async def get_org_history(
    session: Annotated[AsyncSession, Depends(get_session)],
    org_id: str,
    path: Annotated[str, Query(description="datum path, e.g. financial_transparency.income", max_length=200)],
) -> list[DatumHistoryEntry]:
    rows = (
        (
            await session.execute(
                select(OrgDatum).where(OrgDatum.org_id == org_id, OrgDatum.path == path).order_by(OrgDatum.valid_from)
            )
        )
        .scalars()
        .all()
    )
    return [
        DatumHistoryEntry(datum=serialise_datum(row), valid_from=row.valid_from, superseded_at=row.superseded_at)
        for row in rows
    ]
