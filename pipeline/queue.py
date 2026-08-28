"""Draining the ingestion_run queue.

The admin endpoint does not run anything. It writes one `ingestion_run` row with status "queued"
and returns - deliberately, so the API never imports the pipeline and a slow job never holds an
HTTP connection open. That design is only honest if something on the other side actually drains
the queue. Until this module existed nothing did: `accepted: true` was a promise the system had no
way of keeping, which is a worse failure than a 503, because it looks like success.

One tick claims and runs queued rows oldest first. Claiming is a single UPDATE with
FOR UPDATE SKIP LOCKED, so two overlapping cron ticks cannot take the same row and neither blocks
on the other. A job that fails closes its own row as failed and the tick moves on: one bad request
must not strand the ones queued behind it.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from core.logging import get_logger
from core.models import IngestionRun
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.runs import adopt_run, git_sha

log = get_logger("queue")

Job = Callable[..., Awaitable[None]]

# How many queued runs one tick will drain. A bound rather than "everything waiting" so a queue
# that has grown long, or a job that fails fast in a loop, cannot make one cron tick run forever.
# Whatever is left is picked up by the next tick, still oldest first.
MAX_RUNS_PER_TICK = 5


async def claim_next_queued_run(session_factory: async_sessionmaker[AsyncSession]) -> tuple[uuid.UUID, str] | None:
    """Take the oldest queued run and mark it running, atomically. None when the queue is empty.

    SKIP LOCKED rather than a plain ORDER BY: two cron ticks that overlap must take different rows
    instead of one waiting on the other's lock, and a claim that is not atomic with the status
    change would let both run the same job twice.
    """
    async with session_factory() as session:
        oldest = (
            select(IngestionRun.id)
            .where(IngestionRun.status == "queued")
            .order_by(IngestionRun.started_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        claimed = await session.execute(
            update(IngestionRun)
            .where(IngestionRun.id == oldest)
            .values(status="running", git_sha=git_sha())
            .returning(IngestionRun.id, IngestionRun.job)
        )
        row = claimed.first()
        await session.commit()

    if row is None:
        return None
    return row.id, row.job


async def drain_queue(
    session_factory: async_sessionmaker[AsyncSession],
    jobs: dict[str, Job],
    *,
    max_runs: int = MAX_RUNS_PER_TICK,
) -> int:
    """Run the queued requests, oldest first. Returns how many were executed.

    A run whose job name is not registered is closed as failed rather than left queued forever:
    the admin endpoint validates against the same registry, so this can only happen to a row that
    outlived a rename, and a row nothing will ever execute has to stop looking like pending work.
    """
    executed = 0
    while executed < max_runs:
        claim = await claim_next_queued_run(session_factory)
        if claim is None:
            break
        run_id, job_name = claim
        executed += 1

        job = jobs.get(job_name)
        if job is None:
            try:
                async with adopt_run(session_factory, job_name, run_id):
                    raise LookupError(f"queued run requests unregistered job {job_name!r}")
            except LookupError:
                log.error("queued_job_not_registered", extra={"job": job_name, "run_id": str(run_id)})
            continue

        try:
            async with adopt_run(session_factory, job_name, run_id) as handle:
                # Every job takes (session_factory, handle) and opens its own run only when
                # handle is None - which is exactly why the queued row can be handed to it.
                await job(session_factory, handle)
        except Exception:
            # adopt_run has already closed the row as failed with the error on it. The tick
            # continues: one failing request must not strand the ones queued behind it.
            log.exception("queued_job_failed", extra={"job": job_name, "run_id": str(run_id)})

    return executed
