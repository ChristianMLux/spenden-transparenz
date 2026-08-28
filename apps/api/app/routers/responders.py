"""GET /v1/disasters/{glide_id}/responders - the response board. The page that is the product.

Query budget for the unfiltered board is <=4 statements, checked by an SQLAlchemy event listener
in tests/test_contract.py:

1. candidate organisations (only when the board is unfiltered by district/verification/has_response)
2. statements for this disaster, left-joined to their organisation
3. districts for those statements
4. publishers for those statements' reports

The has_register_confirmed / has_audited_financials / has_warnings flags, and the aliases /
local_script fields on OrgRef, do NOT cost extra queries: they are correlated EXISTS/array_agg
subqueries embedded directly in queries 1 and 2, computed by Postgres in the same round trip
rather than fetched with a loop over organisations.

Organisations with no statement are included by default - their absence of a reported response is
information, not a failure state - unless has_response=true is passed. When a district or
verification filter is active, or has_response=true, a zero-statement organisation cannot match it
by definition, so it is not fetched at all; only has_response=false asks for exactly that set, and
then filters are ignored on purpose (an organisation with no reported response anywhere for this
disaster has no response "in Rasuwa" either - that would conflate "found nothing" with "found
nothing scoped to a place it never claimed").

Grouping and pagination happen in Python, not SQL LIMIT/OFFSET, because a SQL-level limit on the
statements query could split one organisation's statements across two pages of the board.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from app.deps import ILIKE_ESCAPE, get_session, ilike_pattern, list_cache
from app.routers.statements import NOT_REJECTED, hydrate_statements
from app.schemas import OrgRef, ResponderCounts, ResponderFlags, ResponderItem
from core.models import (
    OrgAlias,
    Organisation,
    OrgDatum,
    OrgRegistration,
    OrgWarning,
    Report,
    ResponseStatement,
    StatementDistrict,
)
from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import StringConstraints
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/disasters", tags=["disasters"])

# Same closed vocabulary as the Phase 0 stub - a plain regex-pattern string here would change the
# OpenAPI shape (and the TypeScript union type the web team already generated) from an enum to an
# unconstrained pattern-matched string. Note what "sort" does NOT offer: no value that orders by
# verification, because that would rank organisations by how deeply we researched them.
Sort = Literal["latest", "name", "least_data"]
Hq = Literal["local", "international"]

# The pattern belongs on the item, not on the list: Query(pattern=...) on a list[str] constrains
# the array itself, so FastAPI drops the pattern from the schema and pydantic raises at request
# time - district codes would reach the query layer completely unvalidated.
DistrictCode = Annotated[str, StringConstraints(pattern=r"^NP\d{4}$")]
DistrictQuery = Annotated[
    list[DistrictCode],
    Query(description="repeatable district code, e.g. NP0329 (Rasuwa)", examples=[["NP0329"]]),
]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]
OffsetQuery = Annotated[int, Query(ge=0)]
SearchQuery = Annotated[str | None, Query(max_length=80, description="name search, matched case-insensitively")]
OrgTypeQuery = Annotated[list[str], Query(description="repeatable")]
VerificationQuery = Annotated[list[str], Query(description="repeatable, applies to the statement")]


def _flag_columns():
    """Three correlated EXISTS subqueries, embedded as extra SELECT columns wherever Organisation
    is already being fetched, so the flags cost zero additional round trips."""
    has_register_confirmed = (
        select(literal(True))
        .where(OrgRegistration.org_id == Organisation.org_id, OrgRegistration.verification == "register_confirmed")
        .correlate(Organisation)
        .exists()
    )
    has_audited_financials = (
        select(literal(True))
        .where(OrgRegistration.org_id == Organisation.org_id, OrgRegistration.verification == "externally_audited")
        .correlate(Organisation)
        .exists()
    )
    has_warnings = (
        select(literal(True)).where(OrgWarning.org_id == Organisation.org_id).correlate(Organisation).exists()
    )
    return (
        has_register_confirmed.label("has_register_confirmed"),
        has_audited_financials.label("has_audited_financials"),
        has_warnings.label("has_warnings"),
    )


def _org_extra_columns():
    """aliases and local_script, the same way: correlated subqueries embedded as extra SELECT
    columns, not a second round trip. array_agg over zero org_alias rows is NULL in Postgres, not
    an empty array - _org_extras() below is where that gets turned into []."""
    aliases_agg = (
        select(func.array_agg(OrgAlias.alias_norm))
        .where(OrgAlias.org_id == Organisation.org_id)
        .correlate(Organisation)
        .scalar_subquery()
    )
    local_script = (
        select(OrgDatum.value)
        .where(
            OrgDatum.org_id == Organisation.org_id,
            OrgDatum.path == "names.local_script",
            OrgDatum.superseded_at.is_(None),
        )
        .correlate(Organisation)
        .scalar_subquery()
    )
    return aliases_agg.label("aliases_agg"), local_script.label("local_script")


def _org_ref(org: Organisation, aliases: list[str], local_script: str | None) -> OrgRef:
    return OrgRef(
        org_id=org.org_id,
        name_common=org.name_common,
        org_type=org.org_type,
        hq_country=org.hq_country,
        website=org.website,
        aliases=aliases,
        local_script=local_script,
    )


def _flags(row) -> ResponderFlags:
    return ResponderFlags(
        has_register_confirmed=bool(row.has_register_confirmed),
        has_audited_financials=bool(row.has_audited_financials),
        has_warnings=bool(row.has_warnings),
    )


def _org_extras(row) -> tuple[list[str], str | None]:
    return list(row.aliases_agg or []), row.local_script


class _Group:
    __slots__ = ("aliases", "flags", "local_script", "org", "org_name_raw", "pairs")

    def __init__(
        self,
        org: Organisation | None,
        flags: ResponderFlags,
        org_name_raw: str,
        aliases: list[str],
        local_script: str | None,
    ) -> None:
        self.org = org
        self.flags = flags
        self.org_name_raw = org_name_raw
        self.aliases = aliases
        self.local_script = local_script
        self.pairs: list[tuple[ResponseStatement, Report]] = []


async def _fetch_candidate_orgs(
    session: AsyncSession, *, org_type: list[str], hq: str | None, q: str | None
) -> list[tuple[Organisation, object]]:
    reg_flag, audit_flag, warn_flag = _flag_columns()
    aliases_col, local_script_col = _org_extra_columns()
    query = select(Organisation, reg_flag, audit_flag, warn_flag, aliases_col, local_script_col)
    if org_type:
        query = query.where(Organisation.org_type.in_(org_type))
    if hq == "local":
        query = query.where(Organisation.hq_country == "NP")
    elif hq == "international":
        query = query.where(Organisation.hq_country.isnot(None), Organisation.hq_country != "NP")
    if q:
        query = query.where(Organisation.name_common.ilike(ilike_pattern(q), escape=ILIKE_ESCAPE))
    return (await session.execute(query)).all()


async def _fetch_statements(
    session: AsyncSession,
    *,
    glide_id: str,
    district: list[str],
    org_type: list[str],
    verification: list[str],
    hq: str | None,
    q: str | None,
) -> list:
    reg_flag, audit_flag, warn_flag = _flag_columns()
    aliases_col, local_script_col = _org_extra_columns()
    query = (
        select(ResponseStatement, Report, Organisation, reg_flag, audit_flag, warn_flag, aliases_col, local_script_col)
        .join(Report, ResponseStatement.report_id == Report.id)
        .outerjoin(Organisation, ResponseStatement.org_id == Organisation.org_id)
        .where(NOT_REJECTED, Report.disaster_glide_id == glide_id)
    )
    if verification:
        query = query.where(ResponseStatement.verification.in_(verification))
    if district:
        query = query.where(
            ResponseStatement.id.in_(
                select(StatementDistrict.statement_id).where(StatementDistrict.district_code.in_(district))
            )
        )
    if org_type:
        query = query.where(Organisation.org_type.in_(org_type))
    if hq == "local":
        query = query.where(Organisation.hq_country == "NP")
    elif hq == "international":
        query = query.where(Organisation.hq_country.isnot(None), Organisation.hq_country != "NP")
    if q:
        pattern = ilike_pattern(q)
        query = query.where(
            (Organisation.name_common.ilike(pattern, escape=ILIKE_ESCAPE))
            | (ResponseStatement.org_name_raw.ilike(pattern, escape=ILIKE_ESCAPE))
        )
    return (await session.execute(query)).all()


@router.get(
    "/{glide_id}/responders",
    response_model=list[ResponderItem],
    summary="The response board: who reported a response to this crisis, where, with which source.",
    dependencies=[Depends(list_cache)],
)
async def list_responders(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    glide_id: Annotated[str, Path(examples=["ff-2026-000162-npl"])],
    district: DistrictQuery = [],  # noqa: B006
    org_type: OrgTypeQuery = [],  # noqa: B006
    verification: VerificationQuery = [],  # noqa: B006
    hq: Hq | None = None,
    has_response: bool | None = Query(
        default=None,
        description="organisations with no reported response are included by default; they are not a failure state",
    ),
    q: SearchQuery = None,
    sort: Sort = "latest",
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[ResponderItem]:
    groups: dict[str, _Group] = {}

    if has_response is False:
        candidates = await _fetch_candidate_orgs(session, org_type=org_type, hq=hq, q=q)
        # An organisation "has a response" if it has ANY non-rejected statement for this disaster
        # at all - has_response=false is a claim about the whole disaster, not about whatever
        # district/verification filters happen to also be set, so those are deliberately ignored
        # for this exclusion set.
        responded = (
            (
                await session.execute(
                    select(ResponseStatement.org_id)
                    .join(Report, ResponseStatement.report_id == Report.id)
                    .where(NOT_REJECTED, Report.disaster_glide_id == glide_id, ResponseStatement.org_id.isnot(None))
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        responded_ids = set(responded)
        for row in candidates:
            org = row.Organisation
            if org.org_id in responded_ids:
                continue
            aliases, local_script = _org_extras(row)
            groups[org.org_id] = _Group(org, _flags(row), org.name_common, aliases, local_script)
        statements_by_group: dict[str, list] = {key: [] for key in groups}
    else:
        rows = await _fetch_statements(
            session, glide_id=glide_id, district=district, org_type=org_type, verification=verification, hq=hq, q=q
        )
        for row in rows:
            statement, report, org = row.ResponseStatement, row.Report, row.Organisation
            key = org.org_id if org is not None else f"raw:{statement.org_name_raw}"
            if key not in groups:
                aliases, local_script = _org_extras(row)
                groups[key] = _Group(org, _flags(row), statement.org_name_raw, aliases, local_script)
            groups[key].pairs.append((statement, report))

        board_is_unfiltered = not district and not verification and has_response is not True
        if board_is_unfiltered:
            candidates = await _fetch_candidate_orgs(session, org_type=org_type, hq=hq, q=q)
            for row in candidates:
                org = row.Organisation
                if org.org_id in groups:
                    continue
                aliases, local_script = _org_extras(row)
                groups[org.org_id] = _Group(org, _flags(row), org.name_common, aliases, local_script)

        all_pairs = [pair for group in groups.values() for pair in group.pairs]
        statement_outs = await hydrate_statements(session, all_pairs)
        outs_by_statement_id = {out.id: out for out in statement_outs}
        statements_by_group = {
            key: [outs_by_statement_id[s.id] for s, _ in group.pairs] for key, group in groups.items()
        }

    items = []
    for key, group in groups.items():
        outs = statements_by_group[key]
        latest = max((s.happened_on for s in outs if s.happened_on), default=date.min)
        items.append(
            {
                "org": group.org,
                "org_name_raw": group.org_name_raw,
                "aliases": group.aliases,
                "local_script": group.local_script,
                "outs": outs,
                "flags": group.flags,
                "sort_latest": latest,
                "sort_name": (group.org.name_common if group.org else group.org_name_raw).lower(),
            }
        )

    if sort == "name":
        items.sort(key=lambda i: i["sort_name"])
    elif sort == "least_data":
        items.sort(key=lambda i: (len(i["outs"]), i["sort_name"]))
    else:
        items.sort(key=lambda i: (i["sort_latest"], i["sort_name"]), reverse=True)
        items.sort(key=lambda i: i["sort_latest"] == date.min)  # zero-statement orgs always last

    response.headers["X-Total-Count"] = str(len(items))
    page = items[offset : offset + limit]

    return [
        ResponderItem(
            org=_org_ref(item["org"], item["aliases"], item["local_script"]) if item["org"] else None,
            org_name_raw=item["org_name_raw"],
            statements=item["outs"],
            counts=ResponderCounts(
                statements=len(item["outs"]), districts=len({d.code for s in item["outs"] for d in s.districts})
            ),
            flags=item["flags"],
        )
        for item in page
    ]
