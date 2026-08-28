"""Job runner.

    python -m pipeline.cli list
    python -m pipeline.cli run seed_reference
    python -m pipeline.cli drain
    python -m pipeline.cli tick     # what the Railway cron runs

Jobs are registered here by name. The admin endpoint uses the same registry, so a job that is not
in this dict cannot be triggered over HTTP either.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

from core.logging import configure_logging, get_logger
from core.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.db import session_factory
from pipeline.jobs.districts import resolve_districts
from pipeline.jobs.extract import extract_statements
from pipeline.jobs.match import match_orgs
from pipeline.jobs.orgs import ingest_orgs
from pipeline.jobs.reliefweb import fetch_report_bodies, ingest_reliefweb_listing
from pipeline.jobs.seed_reference import seed_reference
from pipeline.queue import MAX_RUNS_PER_TICK, drain_queue

log = get_logger("cli")

Job = Callable[[async_sessionmaker[AsyncSession]], Awaitable[None]]

JOBS: dict[str, Job] = {
    "seed_reference": seed_reference,
    "ingest_orgs": ingest_orgs,
    "ingest_reliefweb_listing": ingest_reliefweb_listing,
    "fetch_report_bodies": fetch_report_bodies,
    "extract_statements": extract_statements,
    "match_orgs": match_orgs,
    "resolve_districts": resolve_districts,
}


async def run_job(name: str, database_url: str | None = None) -> None:
    job = JOBS[name]
    async with session_factory(database_url) as factory:
        await job(factory)


async def drain(max_runs: int, database_url: str | None = None) -> int:
    """Execute the runs the admin endpoint queued."""
    async with session_factory(database_url) as factory:
        return await drain_queue(factory, JOBS, max_runs=max_runs)


# The scheduled sequence, in dependency order: a report has to exist before its body can be
# fetched, a body before it can be extracted, a statement before it can be matched to an
# organisation or resolved to a district. seed_reference and ingest_orgs are deliberately absent -
# they load files from the repository, so they change only when a deploy changes them, and running
# them every tick would be work that is guaranteed to write nothing.
TICK_SEQUENCE = (
    "ingest_reliefweb_listing",
    "fetch_report_bodies",
    "extract_statements",
    "match_orgs",
    "resolve_districts",
)


async def tick(database_url: str | None = None) -> None:
    """One cron tick: drain what was requested, then run the scheduled sequence.

    Each job opens its own ingestion_run, so /v1/meta/freshness reports per job rather than per
    tick, and a job that finds nothing new writes nothing and costs a query. A tick on a quiet
    hour is therefore seconds, not minutes.

    Queued runs go first: someone pressing the admin trigger is asking for something now, and
    making them wait behind a full scheduled sequence would defeat the point of the endpoint.

    One failing job does not abort the tick. The sequence is ordered by dependency, not by
    transaction - if the listing fetch fails, extracting the bodies already in the database is
    still the right thing to do, and the failure is already recorded on that job's own run row.
    """
    async with session_factory(database_url) as factory:
        drained = await drain_queue(factory, JOBS, max_runs=MAX_RUNS_PER_TICK)
        log.info("tick_drained", extra={"executed": drained})

        failed: list[str] = []
        for name in TICK_SEQUENCE:
            try:
                await JOBS[name](factory)
            except Exception as exc:
                failed.append(name)
                log.error("tick_job_failed", extra={"job": name, "error_type": type(exc).__name__})

        log.info("tick_finished", extra={"drained": drained, "ran": len(TICK_SEQUENCE), "failed": failed})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline.cli", description="Run an ingestion job.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list the registered jobs")
    run_parser = subparsers.add_parser("run", help="run one job")
    run_parser.add_argument("job", choices=sorted(JOBS))
    drain_parser = subparsers.add_parser("drain", help="run the jobs the admin endpoint queued, oldest first")
    drain_parser.add_argument("--max", type=int, default=MAX_RUNS_PER_TICK, dest="max_runs")
    subparsers.add_parser("tick", help="one cron tick: drain the queue, then run the scheduled sequence")

    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        service="pipeline",
        secrets=[s.get_secret_value() for s in (settings.admin_token, settings.openrouter_api_key) if s is not None],
    )

    if args.command == "list":
        for name in sorted(JOBS):
            print(name)
        return 0

    if args.command == "drain":
        executed = asyncio.run(drain(args.max_runs))
        log.info("queue_drained", extra={"executed": executed})
        return 0

    if args.command == "tick":
        asyncio.run(tick())
        return 0

    try:
        asyncio.run(run_job(args.job))
    except Exception as exc:
        # The run row is already closed as failed by run_context; this is the operator-facing exit.
        log.error("job_crashed", extra={"job": args.job, "error_type": type(exc).__name__})
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
