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

import psycopg
import pytest
from core.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Locally the model tests get their own database: `spenden` is the Alembic-managed dev database,
# and create_all/drop_all here would fight the migration for it. In CI the service container is
# empty, so TEST_DATABASE_URL can point straight at it.
DEFAULT_TEST_URL = "postgresql+asyncpg://spenden:spenden@localhost:55432/spenden_test"


def test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)


def _ensure_database_exists(url: str) -> None:
    libpq = "postgresql://" + url.partition("://")[2]
    head, _, database = libpq.rpartition("/")
    with psycopg.connect(f"{head}/postgres", autocommit=True) as conn:
        exists = conn.execute("select 1 from pg_database where datname = %s", (database,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{database}"')


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator:
    _ensure_database_exists(test_database_url())
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
