"""Job runner.

    python -m pipeline.cli list
    python -m pipeline.cli run seed_reference

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
from pipeline.jobs.seed_reference import seed_reference

log = get_logger("cli")

Job = Callable[[async_sessionmaker[AsyncSession]], Awaitable[None]]

JOBS: dict[str, Job] = {
    "seed_reference": seed_reference,
}


async def run_job(name: str, database_url: str | None = None) -> None:
    job = JOBS[name]
    async with session_factory(database_url) as factory:
        await job(factory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline.cli", description="Run an ingestion job.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list the registered jobs")
    run_parser = subparsers.add_parser("run", help="run one job")
    run_parser.add_argument("job", choices=sorted(JOBS))

    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        service="pipeline",
        secrets=[s.get_secret_value() for s in (settings.admin_token, settings.anthropic_api_key) if s is not None],
    )

    if args.command == "list":
        for name in sorted(JOBS):
            print(name)
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
