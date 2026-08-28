"""Application factory.

Phase 0 wires the engine, the logging, the security headers and the health router. CORS, the ETag
middleware and the rate limiter are WP-C's, and the two marked places below are where they go, so
that two workers do not invent two different wirings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.deps import limiter
from app.middleware import ETagMiddleware
from app.routers import admin, disasters, health, meta, orgs, responders, statements
from core.db import make_engine, make_sessionmaker
from core.logging import configure_logging, get_logger
from core.settings import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
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
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(health.router)
    for router in (disasters.router, responders.router, orgs.router, statements.router, meta.router, admin.router):
        app.include_router(router)

    return app


app = create_app()
