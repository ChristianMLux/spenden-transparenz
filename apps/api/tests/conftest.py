"""API test fixtures.

The migration tests need a database of their own: the model tests own the main test database via
create_all, and running `alembic upgrade head` into the same schema would collide with them.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

API_DIR = Path(__file__).resolve().parents[1]
REPO = API_DIR.parents[1]

DEFAULT_SYNC_URL = "postgresql+psycopg://spenden:spenden@localhost:55432/spenden"
SCRATCH_DB = "spenden_migrations"


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
