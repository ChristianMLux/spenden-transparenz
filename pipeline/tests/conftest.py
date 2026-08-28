"""Database fixtures for the pipeline jobs.

Jobs are tested against a real Postgres at head, because their whole contract - upsert on natural
keys, never delete, second run writes zero rows - only exists in the database.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO = Path(__file__).resolve().parents[2]
API_DIR = REPO / "apps" / "api"

DEFAULT_SYNC_URL = "postgresql+psycopg://spenden:spenden@localhost:55432/spenden"
JOB_DB_BASE = "spenden_jobs"


def scratch_db(base: str) -> str:
    """A database name unique to this checkout.

    Every worktree points at the same Postgres container, and the names used to be fixed. Two
    workers running their suites at the same time would then DROP the database the other was
    using, which surfaced as ConnectionDoesNotExistError and as rows vanishing between insert and
    read - in test files neither worker had touched. Hashing the repository root gives each
    checkout its own database, stable across runs so the containers do not fill up with strays.
    Override with SPENDEN_TEST_DB_SUFFIX when you want to pin one.
    """
    suffix = (
        os.environ.get("SPENDEN_TEST_DB_SUFFIX")
        or hashlib.blake2s(str(REPO).encode("utf-8"), digest_size=3).hexdigest()
    )
    return f"{base}_{suffix}"


JOB_DB = scratch_db(JOB_DB_BASE)


def _base_sync_url() -> str:
    return os.environ.get("TEST_DATABASE_URL_SYNC", DEFAULT_SYNC_URL)


def _libpq(url: str, database: str) -> str:
    without_driver = "postgresql://" + url.partition("://")[2]
    head, _, _ = without_driver.rpartition("/")
    return f"{head}/{database}"


@pytest.fixture(scope="session")
def job_db_sync_url() -> str:
    """A scratch database migrated to head with Alembic - the same schema production gets."""
    maintenance = _libpq(_base_sync_url(), "postgres")
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{JOB_DB}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{JOB_DB}"')

    url = _libpq(_base_sync_url(), JOB_DB).replace("postgresql://", "postgresql+psycopg://", 1)
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return url


@pytest.fixture(scope="session")
def job_db_url(job_db_sync_url: str) -> str:
    return job_db_sync_url.replace("+psycopg", "+asyncpg", 1)


@pytest.fixture(scope="session")
async def job_engine(job_db_url: str) -> AsyncIterator:
    engine = create_async_engine(job_db_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def job_sessionmaker(job_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(job_engine, expire_on_commit=False)


@pytest.fixture
async def session(job_engine) -> AsyncIterator[AsyncSession]:
    """A read session for assertions. Jobs commit through their own sessions."""
    factory = async_sessionmaker(job_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
async def _clean_tables(job_engine) -> AsyncIterator[None]:
    """Each job test starts from an empty database: idempotency claims are only meaningful when
    the first run is actually the first run."""
    from sqlalchemy import text

    async with job_engine.begin() as conn:
        await conn.execute(
            text(
                "truncate table statement_district, response_statement, report_source, report,"
                " org_datum, org_alias, org_registration, org_warning, organisations,"
                " district_alias, district, source, disaster, ingestion_run restart identity cascade"
            )
        )
    yield
