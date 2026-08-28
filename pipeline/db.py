"""Database access for the jobs.

One engine per process, disposed when the CLI exits. Jobs receive a session factory rather than
reaching for a global, so a test can hand them a scratch database without patching anything.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from core.db import make_engine, make_sessionmaker
from core.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@asynccontextmanager
async def session_factory(database_url: str | None = None) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Yield a session factory bound to a fresh engine, and dispose the engine on the way out."""
    url = database_url or get_settings().async_url
    # Jobs are single-threaded batch work: a large pool would just hold connections open.
    engine = make_engine(url, pool_size=2, max_overflow=0)
    try:
        yield make_sessionmaker(engine)
    finally:
        await engine.dispose()
