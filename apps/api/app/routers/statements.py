"""GET /v1/statements - the chronological stream, and the shared statement-hydration helper that
disasters, orgs and responders all reuse.

hydrate_statements is the one place that turns (response_statement, report) pairs into StatementOut
objects. It always costs exactly two queries - one for districts, one for report publishers - no
matter how many statements are being hydrated, so no caller can turn it into an N+1.

Pagination here fetches every matching row and slices in Python rather than pushing LIMIT/OFFSET
into SQL. That is deliberate at this scale (the pilot dataset is on the order of a few hundred
statements total): the responders board already has to group statements in Python before it can
paginate correctly (a SQL-level LIMIT could split one organisation's statements across pages), so
this endpoint uses the same shape rather than a second, inconsistent pagination strategy. If the
statement count grows past the low thousands, this is the first place to revisit.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from app.deps import get_session, list_cache
from app.schemas import DistrictRef, SourceRef, StatementOut
from core.models import District, Report, ReportSource, ResponseStatement, StatementDistrict
from fastapi import APIRouter, Depends, Query, Response
from pydantic import StringConstraints
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/statements", tags=["statements"])

NOT_REJECTED = ResponseStatement.status != "rejected_unverbatim"

# The pattern belongs on the item, not on the list: Query(pattern=...) on a list[str] constrains
# the array itself, so FastAPI drops the pattern from the schema and pydantic raises at request
# time, and district codes would reach the query layer completely unvalidated.
DistrictCode = Annotated[str, StringConstraints(pattern=r"^NP\d{4}$")]
DistrictQuery = Annotated[
    list[DistrictCode],
    Query(description="repeatable district code, e.g. NP0329 (Rasuwa)", examples=[["NP0329"]]),
]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]
OffsetQuery = Annotated[int, Query(ge=0)]


async def _districts_by_statement(session: AsyncSession, statement_ids: list[int]) -> dict[int, list[DistrictRef]]:
    if not statement_ids:
        return {}
    rows = (
        await session.execute(
            select(StatementDistrict.statement_id, StatementDistrict.resolution, District.code, District.name)
            .join(District, StatementDistrict.district_code == District.code)
            .where(StatementDistrict.statement_id.in_(statement_ids))
        )
    ).all()
    out: dict[int, list[DistrictRef]] = {}
    for row in rows:
        out.setdefault(row.statement_id, []).append(
            DistrictRef(code=row.code, name=row.name, resolution=row.resolution)
        )
    return out


async def _publisher_by_report(session: AsyncSession, report_ids: list[int]) -> dict[int, str | None]:
    if not report_ids:
        return {}
    rows = (
        await session.execute(
            select(ReportSource.report_id, ReportSource.publisher).where(ReportSource.report_id.in_(report_ids))
        )
    ).all()
    grouped: dict[int, list[str]] = {}
    for row in rows:
        grouped.setdefault(row.report_id, []).append(row.publisher)
    return {report_id: ", ".join(sorted(publishers)) for report_id, publishers in grouped.items()}


def _statement_out(
    statement: ResponseStatement, report: Report, districts: list[DistrictRef], publisher: str | None
) -> StatementOut:
    return StatementOut(
        id=statement.id,
        activity=statement.activity,
        activity_type=statement.activity_type,
        districts=districts,
        happened_on=statement.happened_on,
        amount=statement.amount,
        currency=statement.currency,
        amount_basis=statement.amount_basis,
        quote=statement.quote,
        source=SourceRef(
            url=report.url,
            publisher=publisher,
            published_at=report.published_at,
            verification=statement.verification,
        ),
    )


async def hydrate_statements(
    session: AsyncSession, pairs: list[tuple[ResponseStatement, Report]]
) -> list[StatementOut]:
    """Turn already-fetched (statement, report) pairs into StatementOut objects.

    Exactly two queries total (districts, publishers) regardless of len(pairs): the board that is
    the product must not also be the one that issues a query per row.
    """
    statement_ids = [statement.id for statement, _ in pairs]
    report_ids = list({report.id for _, report in pairs})
    districts_by_statement = await _districts_by_statement(session, statement_ids)
    publisher_by_report = await _publisher_by_report(session, report_ids)
    return [
        _statement_out(
            statement, report, districts_by_statement.get(statement.id, []), publisher_by_report.get(report.id)
        )
        for statement, report in pairs
    ]


def statement_query(*, glide_id: str | None = None, org_id: str | None = None, district: list[str] | None = None):
    """The filter vocabulary shared with responders.py: same disaster/org/district predicates."""
    query = select(ResponseStatement, Report).join(Report, ResponseStatement.report_id == Report.id).where(NOT_REJECTED)
    if glide_id:
        query = query.where(Report.disaster_glide_id == glide_id)
    if org_id:
        query = query.where(ResponseStatement.org_id == org_id)
    if district:
        query = query.where(
            ResponseStatement.id.in_(
                select(StatementDistrict.statement_id).where(StatementDistrict.district_code.in_(district))
            )
        )
    return query


@router.get("", response_model=list[StatementOut], summary="Chronological stream of reported responses.")
async def list_statements(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    _cache: Annotated[None, Depends(list_cache)],
    glide_id: str | None = None,
    district: DistrictQuery = [],  # noqa: B006 - FastAPI reads the default to build the schema
    org_id: str | None = None,
    since: Annotated[date | None, Query(description="ISO date, inclusive")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[StatementOut]:
    query = statement_query(glide_id=glide_id, org_id=org_id, district=district)
    if since:
        query = query.where(ResponseStatement.happened_on >= since)
    query = query.order_by(ResponseStatement.happened_on.desc().nullslast(), ResponseStatement.created_at.desc())

    pairs = [(row.ResponseStatement, row.Report) for row in (await session.execute(query)).all()]
    response.headers["X-Total-Count"] = str(len(pairs))
    page = pairs[offset : offset + limit]
    return await hydrate_statements(session, page)
