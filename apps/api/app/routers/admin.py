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

Triggering a job starts it via BackgroundTasks and returns immediately; it does not await
completion. `extract_statements` is capped at 25 reports and makes one LLM call each, so a run can
take minutes - long enough that Railway's proxy would time the connection out before an in-process
`await run_job(job)` returned, either handing the caller a 502 for a job that is still running, or
killing it mid-run, which is exactly the state ingestion_run bookkeeping exists to avoid.
`accepted` means "the job was started," not "the job finished"; the caller learns the outcome from
GET /v1/admin/runs, which is what that route is for. The 404 for an unknown job name still happens
synchronously, before anything is scheduled.

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
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/admin", tags=["admin"])
log = get_logger("admin")

LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]


async def _run_and_log(job: str) -> None:
    """Runs after the response is already sent. Errors cannot reach the caller from here - they
    would only vanish into the ASGI server's logs - so pipeline.runs.run_context's own failure
    bookkeeping in ingestion_run is the record of truth, and this just makes sure the failure is
    visible in this process's logs too."""
    from pipeline.cli import run_job  # see module docstring for why this import is deferred

    try:
        await run_job(job)
    except Exception:
        log.warning("admin_triggered_job_failed", extra={"job": job})


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
    background_tasks: BackgroundTasks,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> AcceptedOut:
    require_admin_token(x_admin_token)

    from pipeline.cli import JOBS  # see module docstring for why this import is deferred

    if job not in JOBS:
        raise HTTPException(status_code=404, detail=f"unknown job: {job}")

    background_tasks.add_task(_run_and_log, job)
    return AcceptedOut(accepted=True, job=job, run_id=None)


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
