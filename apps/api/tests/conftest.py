"""API test fixtures.

The migration tests need a database of their own: the model tests own the main test database via
create_all, and running `alembic upgrade head` into the same schema would collide with them.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from app.main import create_app
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
REPO = API_DIR.parents[1]

DEFAULT_SYNC_URL = "postgresql+psycopg://spenden:spenden@localhost:55432/spenden"
SCRATCH_DB_BASE = "spenden_migrations"


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


SCRATCH_DB = scratch_db(SCRATCH_DB_BASE)


def base_sync_url() -> str:
    return os.environ.get("TEST_DATABASE_URL_SYNC", DEFAULT_SYNC_URL)


def _psycopg_url(url: str, database: str) -> str:
    """Turn a SQLAlchemy URL into a libpq one pointing at `database`."""
    without_driver = "postgresql://" + url.partition("://")[2]
    head, _, _ = without_driver.rpartition("/")
    return f"{head}/{database}"


@pytest.fixture(scope="session")
def scratch_db_url() -> Iterator[str]:
    """A freshly created, empty database, dropped again afterwards."""
    maintenance = _psycopg_url(base_sync_url(), "postgres")
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{SCRATCH_DB}"')
    yield _psycopg_url(base_sync_url(), SCRATCH_DB).replace("postgresql://", "postgresql+psycopg://", 1)
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)')


def _alembic_config(url: str) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def alembic_config() -> Callable[[str], Config]:
    """Builds an Alembic config pointed at a given database. A fixture rather than an import,
    so the test modules do not have to make `tests` an importable package."""
    return _alembic_config


@pytest.fixture
async def client_no_db() -> AsyncIterator[AsyncClient]:
    """The stub routes serve no data, so they need no database. Building the client without one
    also proves that: a stub route that quietly queried Postgres would fail here."""
    app = create_app(database_url=None)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture(scope="session")
def migrated(scratch_db_url: str) -> str:
    """The scratch database at head. Shared by the migration tests and the API tests."""
    command.upgrade(_alembic_config(scratch_db_url), "head")
    return scratch_db_url
