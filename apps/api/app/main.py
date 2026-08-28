"""Application factory.

Phase 0 wires the engine, the logging, the security headers and the health router. CORS, the ETag
middleware and the rate limiter are WP-C's, and the two marked places below are where they go, so
that two workers do not invent two different wirings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.routers import health, stubs
from core.db import make_engine, make_sessionmaker
from core.logging import configure_logging, get_logger
from core.settings import get_settings
from fastapi import FastAPI
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
    # WP-C adds here, in this order: ETagMiddleware, then CORSMiddleware, then the slowapi limiter.

    app.include_router(health.router)
    # Phase 0 ships the routes as typed stubs so the web team can generate lib/types.ts and
    # start building. WP-C replaces app/routers/stubs.py with the six real routers and must
    # not change a path, a parameter or a field name without telling both leads.
    for router in stubs.ROUTERS:
        app.include_router(router)

    return app


app = create_app()
