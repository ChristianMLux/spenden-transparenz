"""POST /v1/admin/ingest/{job}, GET /v1/admin/runs.

Both routes are always 401 without a valid X-Admin-Token, never a distinct status for "no token
configured" (see app.deps.require_admin_token for why), and rate-limited at 5/minute instead of
the public 60/minute because these routes trigger real work, not reads.

The admin-token check happens INSIDE the function body, after the @limiter.limit decorator's own
check, not as a router-level FastAPI dependency. slowapi's decorator checks the rate limit before
calling the wrapped function; a router-level `Depends(require_admin_token)` would resolve - and
could raise 401 - before FastAPI ever calls that wrapped function, so a caller hammering the
endpoint with wrong tokens would never trip the rate limit at all. Checking the token inside the
body puts the 401 after the rate-limit check, so brute-forcing the token is throttled like
everything else here.

Triggering a job runs it in-process, awaiting completion, and then reports the ingestion_run row
that pipeline.runs.run_context wrote - run_context always closes that row, including on failure,
so there is always something to report back even when the job raised.

The `pipeline.cli` import is deliberately deferred to inside trigger_ingest(), not at module level.
`pipeline/pyproject.toml` documents pipeline as a virtual project with no build-system, run from
the repository root as its own Railway service - it is not installed as a library and is not a
dependency of apps/api/requirements.txt. Importing it eagerly here breaks anything that only needs
to introspect this module (apps/api/scripts/export_openapi.py adds only apps/api to sys.path, not
the repo root, so `import pipeline` fails there today) and is unverified to resolve at all under
however the api service ends up deployed on Railway. Flagged to the backend lead; see the WP-C
report for the open question this leaves for PO-5.
"""

from __future__ import annotations

from typing import Annotated

from app.deps import ADMIN_LIMIT, get_session, limiter, no_store, require_admin_token
from app.schemas import AcceptedOut, RunOut
from core.logging import get_logger
from core.models import IngestionRun
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/admin", tags=["admin"])
log = get_logger("admin")

LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]


@router.post(
    "/ingest/{job}",
    response_model=AcceptedOut,
    summary="Trigger one ingestion job.",
    dependencies=[Depends(no_store)],
)
@limiter.limit(ADMIN_LIMIT)
async def trigger_ingest(
    request: Request,
    job: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> AcceptedOut:
    require_admin_token(x_admin_token)

    from pipeline.cli import JOBS, run_job  # see module docstring for why this import is deferred

    if job not in JOBS:
        raise HTTPException(status_code=404, detail=f"unknown job: {job}")

    accepted = True
    try:
        await run_job(job)
    except Exception:
        # run_context already closed the ingestion_run row as failed; the trigger itself still
        # succeeded, so this is reported through the response body, not a 500.
        log.warning("admin_triggered_job_failed", extra={"job": job})
        accepted = False

    latest = (
        await session.execute(
            select(IngestionRun.id).where(IngestionRun.job == job).order_by(IngestionRun.started_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return AcceptedOut(accepted=accepted, job=job, run_id=str(latest) if latest else None)


@router.get(
    "/runs",
    response_model=list[RunOut],
    summary="Recent ingestion runs.",
    dependencies=[Depends(no_store)],
)
@limiter.limit(ADMIN_LIMIT)
async def list_runs(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: LimitQuery = 50,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> list[RunOut]:
    require_admin_token(x_admin_token)

    rows = (
        (await session.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)))
        .scalars()
        .all()
    )
    return [
        RunOut(
            id=str(row.id),
            job=row.job,
            status=row.status,
            started_at=row.started_at,
            finished_at=row.finished_at,
            rows_written=row.rows_written,
            rows_skipped=row.rows_skipped,
            rows_rejected=row.rows_rejected,
            cost_usd=row.cost_usd,
            git_sha=row.git_sha,
            error=row.error,
        )
        for row in rows
    ]
