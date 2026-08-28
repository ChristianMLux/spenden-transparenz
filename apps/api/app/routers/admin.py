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

The admin endpoint QUEUES; it does not run. It validates the job name against core.jobs.JOB_NAMES,
inserts one ingestion_run row with status="queued", and returns. Nothing pipeline-related is
imported here at all: the API and the pipeline are separate Railway services with separate deploy
artefacts, and the pipeline carries the LLM credentials and the network fetchers - none of which
belong in a read-only public API's image. The pipeline service drains queued runs on its own next
tick. `accepted` means "recorded, and the pipeline will drain it", not "finished"; the caller
learns the outcome from GET /v1/admin/runs. This also means nothing long-running ever happens
inside a web request, so there is no Railway proxy timeout to worry about either.
"""

from __future__ import annotations

from typing import Annotated

from app.deps import ADMIN_LIMIT, get_session, limiter, no_store, require_admin_token
from app.schemas import AcceptedOut, RunOut
from core.jobs import JOB_NAMES
from core.models import IngestionRun
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/admin", tags=["admin"])

LimitQuery = Annotated[int, Query(ge=1, le=100, description="page size, at most 100")]


@router.post(
    "/ingest/{job}",
    response_model=AcceptedOut,
    summary="Queue one ingestion job. The pipeline service drains it; this does not run it.",
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

    if job not in JOB_NAMES:
        raise HTTPException(status_code=404, detail=f"unknown job: {job}")

    run = IngestionRun(job=job, status="queued")
    session.add(run)
    await session.flush()
    run_id = str(run.id)
    # get_session() rolls back in its own finally block on the way out, so the write has to be
    # committed here or it would vanish - the rollback after an already-committed transaction is
    # a harmless no-op, but skipping the commit is not.
    await session.commit()

    return AcceptedOut(accepted=True, job=job, run_id=run_id)


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
