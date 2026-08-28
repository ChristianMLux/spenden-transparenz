"""Application factory.

Phase 0 wires the engine, the logging, the security headers and the health router. CORS, the ETag
middleware and the rate limiter are WP-C's, and the two marked places below are where they go, so
that two workers do not invent two different wirings.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.deps import enforce_get_rate_limit, limiter
from app.middleware import ETagMiddleware
from app.routers import admin, disasters, health, meta, orgs, responders, statements
from core.db import make_engine, make_sessionmaker
from core.logging import configure_logging, get_logger
from core.settings import get_settings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = get_logger("api")

DESCRIPTION = (
    "Who is responding to a disaster, where, since when, and from which source. "
    "Every value carries its provenance; a missing value is an explicit, visible state. "
    "This API does not rate, score or rank organisations."
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # Read-only JSON API: nothing here should ever be framed or execute script.
    "X-Frame-Options": "DENY",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response


EXPECTED_REVISION_FILE_GLOB = "*.py"


def _code_head_revision() -> str | None:
    """The newest migration revision this deployment's code carries, read from the files.

    Deliberately parsed from the versions directory rather than imported through Alembic: this
    runs at start-up, on every boot, and must not need alembic.ini, a database connection, or a
    working directory to answer. A file it cannot parse is skipped rather than fatal - a start-up
    check that can prevent the app from starting is a worse failure than the one it looks for.
    """
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    revisions: set[str] = set()
    downs: set[str] = set()
    try:
        files = sorted(versions.glob(EXPECTED_REVISION_FILE_GLOB))
    except OSError:
        return None
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            continue
        revision = re.search(r"^revision: str = ['\"]([^'\"]+)['\"]", text, re.MULTILINE)
        down = re.search(r"^down_revision: [^=]+= ['\"]([^'\"]+)['\"]", text, re.MULTILINE)
        if revision:
            revisions.add(revision.group(1))
        if down:
            downs.add(down.group(1))
    heads = revisions - downs
    return heads.pop() if len(heads) == 1 else None


async def _warn_if_schema_is_behind_the_code(app: FastAPI) -> None:
    """Say so, loudly, at start-up when the database has not been migrated to this code's head.

    This exists because of a real 500. Code at migration 0006 against a database at 0005 answered
    /health with 200 - it deliberately does not touch Postgres - while every request to the board
    failed with `column org_datum.channel_type does not exist`. The signal existed (/health/ready
    reports the revision) and nothing was reading it, so the first evidence was a stack trace.

    On Railway the window is real: a pre-deploy `alembic upgrade head` that fails still leaves the
    API starting, and a rolling deploy has a new-code/old-schema moment by construction.

    A warning, not a refusal to start. Which is right is not obvious - a hard exit would turn a
    migration that has not run yet into an outage - but a deployment that can still serve
    /health/ready and its unaffected routes is more useful than one that will not boot, and the
    log line names the fix.
    """
    expected = _code_head_revision()
    factory = getattr(app.state, "sessionmaker", None)
    if expected is None or factory is None:
        return
    try:
        async with factory() as session:
            actual = (await session.execute(text("select version_num from alembic_version"))).scalar_one_or_none()
    except Exception as exc:
        log.warning("schema_revision_check_failed", extra={"error_type": type(exc).__name__})
        return
    if actual != expected:
        log.error(
            "schema_behind_code",
            extra={"database_revision": actual, "code_revision": expected},
        )
    else:
        log.info("schema_revision_ok", extra={"revision": actual})


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        service="api",
        secrets=[s.get_secret_value() for s in (settings.admin_token, settings.openrouter_api_key) if s is not None],
        capture_uvicorn=True,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        url = database_url or (settings.database_url and settings.async_url)
        if url:
            app.state.engine = make_engine(url)
            app.state.sessionmaker = make_sessionmaker(app.state.engine)
        else:
            # Development without a database: /health still answers, /health/ready says so.
            app.state.engine = None
            app.state.sessionmaker = None
            log.warning("started_without_database")
        await _warn_if_schema_is_behind_the_code(app)
        log.info("api_started", extra={"env": settings.env})
        yield
        if app.state.engine is not None:
            await app.state.engine.dispose()
        log.info("api_stopped")

    app = FastAPI(
        title="Spenden-Transparenz API",
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        # Open-data API: the docs are part of the product, not an accident.
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    # In this order: ETagMiddleware, then CORSMiddleware, then the slowapi limiter. Starlette
    # wraps outside-in in the order middleware is added, so this is (outermost first) security
    # headers -> ETag -> CORS -> rate limiting -> routes.
    app.add_middleware(ETagMiddleware)
    app.add_middleware(
        CORSMiddleware,
        # Exact origins only, never "*": Settings already rejects a wildcard at validation time,
        # so an empty list here just means no browser origin is allowed yet, not an open CORS
        # policy. GET/OPTIONS only - this is a read-only API.
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["X-Admin-Token"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # No SlowAPIMiddleware. It cannot enforce anything here: it resolves the handler through
    # `hasattr(route, "endpoint")`, and this FastAPI version wraps an included router in an
    # _IncludedRouter that matches FULL and has no `endpoint`, so slowapi finds no handler and
    # treats the request as exempt. Registering it would say "GETs are rate limited" while every
    # request passed through untouched, which is worse than not registering it. The read limit is
    # a router dependency (deps.enforce_get_rate_limit); the admin limit is a route decorator,
    # which is checked inside the endpoint and never needed the middleware.
    app.include_router(health.router)
    for router in (disasters.router, responders.router, orgs.router, statements.router, meta.router, admin.router):
        app.include_router(router, dependencies=[Depends(enforce_get_rate_limit)])

    return app


app = create_app()
