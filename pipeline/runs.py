"""The run contract every ingestion job follows.

A job opens an ingestion_run, upserts on natural keys, never deletes, and closes the run in a
finally block - including when it raises. A run left in `running` would make /v1/meta/freshness
lie about when the data was last updated, so there is no path out of this context manager that
leaves one behind.

Counters are explicit rather than inferred. "rows_written" means rows whose content actually
changed; re-writing an identical row counts as skipped. Without that distinction the "second run
writes zero rows" contract cannot be checked, and an upsert that rewrites everything every time
looks exactly like an upsert that does nothing.
"""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from core.logging import get_logger
from core.models import IngestionRun
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

log = get_logger("runs")
REPO = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def git_sha() -> str | None:
    """Which code produced these rows. Cached: this is a subprocess, not a free call."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


@dataclass
class RunHandle:
    """Counters a job reports into. Jobs call count(); nothing else writes these."""

    id: uuid.UUID
    written: int = 0
    skipped: int = 0
    rejected: int = 0
    cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    tokens_in: int = 0
    tokens_out: int = 0

    def count(self, *, written: int = 0, skipped: int = 0, rejected: int = 0) -> None:
        self.written += written
        self.skipped += skipped
        self.rejected += rejected

    def spend(self, *, cost_usd: Decimal | float = 0, tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.cost_usd += Decimal(str(cost_usd))
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out


@asynccontextmanager
async def run_context(
    session_factory: async_sessionmaker[AsyncSession],
    job: str,
) -> AsyncIterator[RunHandle]:
    """Open an ingestion_run, yield its handle, and close it whatever happens."""
    async with session_factory() as session:
        run = IngestionRun(job=job, status="running", git_sha=git_sha())
        session.add(run)
        await session.commit()
        run_id = run.id

    handle = RunHandle(id=run_id)
    log.info("job_started", extra={"job": job, "run_id": str(run_id)})
    error: BaseException | None = None
    try:
        yield handle
    except BaseException as exc:
        error = exc
        raise
    finally:
        # A separate session: the job's own session may be in a failed transaction, and the run
        # row has to be closed regardless.
        async with session_factory() as session:
            row = await session.get(IngestionRun, run_id)
            row.status = "failed" if error is not None else "succeeded"
            row.finished_at = datetime.now(UTC)
            row.rows_written = handle.written
            row.rows_skipped = handle.skipped
            row.rows_rejected = handle.rejected
            row.cost_usd = handle.cost_usd or None
            row.tokens_in = handle.tokens_in or None
            row.tokens_out = handle.tokens_out or None
            if error is not None:
                row.error = f"{type(error).__name__}: {error}"[:2000]
            await session.commit()
        log.info(
            "job_finished",
            extra={
                "job": job,
                "run_id": str(run_id),
                "status": "failed" if error is not None else "succeeded",
                "written": handle.written,
                "skipped": handle.skipped,
                "rejected": handle.rejected,
            },
        )
