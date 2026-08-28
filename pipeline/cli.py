"""Job runner.

    python -m pipeline.cli list
    python -m pipeline.cli run seed_reference
    python -m pipeline.cli drain

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
    """Execute the runs the admin endpoint queued. This is what the cron calls."""
    async with session_factory(database_url) as factory:
        return await drain_queue(factory, JOBS, max_runs=max_runs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline.cli", description="Run an ingestion job.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list the registered jobs")
    run_parser = subparsers.add_parser("run", help="run one job")
    run_parser.add_argument("job", choices=sorted(JOBS))
    drain_parser = subparsers.add_parser("drain", help="run the jobs the admin endpoint queued, oldest first")
    drain_parser.add_argument("--max", type=int, default=MAX_RUNS_PER_TICK, dest="max_runs")

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

    try:
        asyncio.run(run_job(args.job))
    except Exception as exc:
        # The run row is already closed as failed by run_context; this is the operator-facing exit.
        log.error("job_crashed", extra={"job": args.job, "error_type": type(exc).__name__})
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
