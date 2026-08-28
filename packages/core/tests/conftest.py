"""Database fixtures for the model tests.

These tests need a real Postgres: the invariants they check are CHECK constraints, generated
columns and partial unique indexes, none of which exist outside the database. SQLite would pass
every one of them for the wrong reason, which is why the spec rules it out.

Local: docker compose -f docker-compose.dev.yml up -d
CI:    the postgres:16 service container, via TEST_DATABASE_URL.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from core.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_TEST_URL = "postgresql+asyncpg://spenden:spenden@localhost:55432/spenden"


def test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator:
    engine = create_async_engine(test_database_url(), poolclass=None)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except OSError as exc:  # no database reachable: fail loudly, never skip silently
        pytest.fail(
            f"cannot reach {test_database_url()}: {exc}. Start it with: docker compose -f docker-compose.dev.yml up -d"
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """A session whose work is always rolled back, so tests cannot see each other's rows."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
