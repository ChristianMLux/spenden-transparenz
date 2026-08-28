"""Health and readiness.

/health is the Railway healthcheck. It must answer without touching Postgres, or a database
restart takes the API down with it. /health/ready is the one that reports the database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from app.main import create_app
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
UNREACHABLE = "postgresql+asyncpg://spenden:spenden@localhost:1/spenden"


async def _client(database_url: str) -> AsyncIterator[AsyncClient]:
    app = create_app(database_url=database_url)
    # ASGITransport does not run lifespan events, so the engine would never be created.
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture
async def client(migrated: str) -> AsyncIterator[AsyncClient]:
    async for c in _client(migrated.replace("+psycopg", "+asyncpg", 1)):
        yield c


@pytest.fixture
async def client_with_broken_db() -> AsyncIterator[AsyncClient]:
    async for c in _client(UNREACHABLE):
        yield c


async def test_health_is_200_and_does_not_touch_the_database(client_with_broken_db: AsyncClient):
    """Deliberately uses the broken-database client: if this passes there, /health is independent."""
    response = await client_with_broken_db.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_health_is_never_cached(client: AsyncClient):
    response = await client.get("/health")
    assert response.headers["cache-control"] == "no-store"


async def test_ready_reports_the_database_and_the_migration_revision(client: AsyncClient, alembic_config):
    """Compared against the actual head rather than a hardcoded revision: pinning "0001" here
    turns every future migration into a spurious failure, which teaches people to edit the test."""
    head = ScriptDirectory.from_config(alembic_config("postgresql+psycopg://unused/unused")).get_current_head()
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["alembic_revision"] == head


async def test_ready_is_503_when_the_database_is_unreachable(client_with_broken_db: AsyncClient):
    response = await client_with_broken_db.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


async def test_ready_never_leaks_the_connection_string(client_with_broken_db: AsyncClient):
    """A failing readiness probe must not print credentials into a public response body."""
    response = await client_with_broken_db.get("/health/ready")
    assert "spenden:spenden" not in response.text
    assert "postgresql" not in response.text.lower()


async def test_security_headers_are_present(client: AsyncClient):
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


async def test_the_app_adds_no_server_banner(client: AsyncClient):
    response = await client.get("/health")
    assert "server" not in {k.lower() for k in response.headers}


def test_the_production_start_command_disables_the_server_banner_and_trusts_the_proxy():
    """uvicorn, not the app, emits the Server header, so the flag lives in the start command."""
    start = (API_DIR / "start.sh").read_text(encoding="utf-8")
    assert "--no-server-header" in start
    assert "--proxy-headers" in start


async def test_docs_stay_public(client: AsyncClient):
    """This is an open-data API. /docs is a feature, not an oversight."""
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200
