"""Phase 0 stubs: the real routes with their real signatures and no data behind them.

The web team generates its types from these. WP-C replaces the bodies and must not change a path,
a parameter or a field name without telling both leads.

Every response carries X-Stub: true, so a stub build can never be mistaken for a working API in a
browser, a screenshot or a test.

WP-C owns this file's successors: disasters.py, responders.py, orgs.py, statements.py, meta.py,
admin.py. Deleting this file is part of WP-C's job.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal

from app.schemas import (
    AcceptedOut,
    DatumHistoryEntry,
    DisasterOut,
    DistrictOut,
    EnumsOut,
    FreshnessOut,
    OrgDetail,
    ResponderItem,
    RunOut,
    SourceOut,
    StatementOut,
)
from core import enums
from fastapi import APIRouter, Header, HTTPException, Path, Query, Response
from pydantic import StringConstraints

STUB = {"X-Stub": "true"}

# Filter vocabulary shared by the list endpoints. Note what is absent: there is no sort option
# that orders by verification, because that would rank organisations by how deeply we researched
# them rather than by anything about them.
Sort = Literal["latest", "name", "least_data"]
Hq = Literal["local", "international"]

# The pattern belongs on the item, not on the list. Query(pattern=...) on a list[str] applies the
# constraint to the array itself: FastAPI drops it from the schema and pydantic raises at request
# time. Written that way, district codes reach the query layer completely unvalidated.
DistrictCode = Annotated[str, StringConstraints(pattern=r"^NP\d{4}$")]
DistrictQuery = Annotated[
    list[DistrictCode],
    Query(description="repeatable district code, e.g. NP0329 (Rasuwa)", examples=[["NP0329"]]),
]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]
OffsetQuery = Annotated[int, Query(ge=0)]
SearchQuery = Annotated[str | None, Query(max_length=80, description="name search, matched case-insensitively")]

disasters = APIRouter(prefix="/v1/disasters", tags=["disasters"])
orgs = APIRouter(prefix="/v1/orgs", tags=["organisations"])
statements = APIRouter(prefix="/v1/statements", tags=["statements"])
meta = APIRouter(prefix="/v1/meta", tags=["meta"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


def _stub(response: Response, cache: str = "public, max-age=60, stale-while-revalidate=600") -> None:
    response.headers.update(STUB)
    response.headers["Cache-Control"] = cache


@disasters.get("", response_model=list[DisasterOut], summary="Crises with a response board.")
async def list_disasters(response: Response) -> list[DisasterOut]:
    _stub(response)
    return []


@disasters.get("/{glide_id}", response_model=DisasterOut, summary="One crisis by its GLIDE id.")
async def get_disaster(
    response: Response,
    glide_id: Annotated[str, Path(examples=["ff-2026-000162-npl"])],
) -> DisasterOut:
    _stub(response)
    raise HTTPException(status_code=404, detail="not found (stub)")


@disasters.get(
    "/{glide_id}/responders",
    response_model=list[ResponderItem],
    summary="The response board: who reported a response to this crisis, where, with which source.",
)
async def list_responders(
    response: Response,
    glide_id: Annotated[str, Path(examples=["ff-2026-000162-npl"])],
    district: DistrictQuery = [],  # noqa: B006 - FastAPI reads the default to build the schema
    org_type: Annotated[list[str], Query(description="repeatable")] = [],  # noqa: B006
    verification: Annotated[list[str], Query(description="repeatable, applies to the statement")] = [],  # noqa: B006
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
    _stub(response)
    response.headers["X-Total-Count"] = "0"
    return []


@orgs.get("", response_model=list[OrgDetail], summary="Organisations.")
async def list_orgs(
    response: Response,
    org_type: Annotated[list[str], Query(description="repeatable")] = [],  # noqa: B006
    hq: Hq | None = None,
    q: SearchQuery = None,
    sort: Sort = "name",
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[OrgDetail]:
    _stub(response)
    response.headers["X-Total-Count"] = "0"
    return []


@orgs.get("/{org_id}", response_model=OrgDetail, summary="One organisation, gaps included.")
async def get_org(response: Response, org_id: str) -> OrgDetail:
    _stub(response, cache="public, max-age=300")
    raise HTTPException(status_code=404, detail="not found (stub)")


@orgs.get("/{org_id}/history", response_model=list[DatumHistoryEntry], summary="How one value changed.")
async def get_org_history(
    response: Response,
    org_id: str,
    path: Annotated[str, Query(description="datum path, e.g. financial_transparency.income", max_length=200)],
) -> list[DatumHistoryEntry]:
    _stub(response, cache="public, max-age=300")
    return []


@statements.get("", response_model=list[StatementOut], summary="Chronological stream of reported responses.")
async def list_statements(
    response: Response,
    glide_id: str | None = None,
    district: DistrictQuery = [],  # noqa: B006
    org_id: str | None = None,
    since: Annotated[str | None, Query(description="ISO date, inclusive")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> list[StatementOut]:
    _stub(response)
    response.headers["X-Total-Count"] = "0"
    return []


@meta.get("/districts", response_model=list[DistrictOut], summary="The 77 Nepali districts.")
async def list_districts(response: Response) -> list[DistrictOut]:
    _stub(response, cache="public, max-age=3600")
    return []


@meta.get("/sources", response_model=list[SourceOut], summary="Sources with their licences.")
async def list_sources(response: Response) -> list[SourceOut]:
    _stub(response, cache="public, max-age=3600")
    return []


@meta.get("/enums", response_model=EnumsOut, summary="Enum values, so the frontend hardcodes none.")
async def get_enums(response: Response) -> EnumsOut:
    _stub(response, cache="public, max-age=3600")
    return EnumsOut(enums={name: list(values) for name, values in enums.ALL_ENUMS.items()})


@meta.get("/freshness", response_model=FreshnessOut, summary="When each job last succeeded.")
async def get_freshness(response: Response) -> FreshnessOut:
    _stub(response, cache="public, max-age=3600")
    return FreshnessOut(generated_at=datetime.now(UTC), jobs=[])


def _require_admin_token(supplied: str | None) -> None:
    """Constant-time comparison. No configured token means closed, never open.

    Always 401, never a distinct status for "no token is configured": that would tell an
    unauthenticated caller which deployments have an unset ADMIN_TOKEN. Production cannot reach
    that state anyway - core.settings refuses to start without one.

    The stub enforces this too. A build where the ingestion trigger is open is exactly the build
    someone deploys by accident.
    """
    from core.settings import get_settings

    configured = get_settings().admin_token
    expected = configured.get_secret_value() if configured is not None else ""
    # compare_digest on both branches: an early return for "no token" would leak the same fact
    # through timing that the status code was hiding.
    if not secrets.compare_digest(supplied or "", expected) or not expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


@admin.post("/ingest/{job}", response_model=AcceptedOut, summary="Trigger one ingestion job.")
async def trigger_ingest(
    response: Response,
    job: str,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> AcceptedOut:
    _require_admin_token(x_admin_token)
    response.headers.update(STUB)
    response.headers["Cache-Control"] = "no-store"
    return AcceptedOut(accepted=False, job=job, run_id=None)


@admin.get("/runs", response_model=list[RunOut], summary="Recent ingestion runs.")
async def list_runs(
    response: Response,
    limit: LimitQuery = 50,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> list[RunOut]:
    _require_admin_token(x_admin_token)
    response.headers.update(STUB)
    response.headers["Cache-Control"] = "no-store"
    return []


ROUTERS = (disasters, orgs, statements, meta, admin)
