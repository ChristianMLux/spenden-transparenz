"""Liveness and readiness.

/health answers from the process alone. It is the Railway healthcheck, and if it queried Postgres
then a database restart would also restart the API. /health/ready is the one that reports the
database, and it reports it without ever naming the connection string.

/health is exempt from the rate limit for the same reason it does not query Postgres. Every
request through Railway shares one rate-limit key - the proxy's own address - so a busy minute
would otherwise answer the healthcheck with 429 and restart a container that was working fine,
the rate limit taking the service down instead of protecting it.
"""

from __future__ import annotations

from app.deps import limiter
from core.logging import get_logger
from fastapi import APIRouter, Request, Response
from sqlalchemy import text

router = APIRouter(tags=["health"])
log = get_logger("health")

NO_STORE = {"Cache-Control": "no-store"}


@router.get("/health", summary="Liveness. Answers without touching the database.")
@limiter.exempt
async def health(request: Request, response: Response) -> dict[str, str]:
    response.headers.update(NO_STORE)
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness. Reports the database and the migration revision.")
async def ready(request: Request, response: Response) -> dict[str, str | None]:
    response.headers.update(NO_STORE)
    factory = getattr(request.app.state, "sessionmaker", None)
    if factory is None:
        response.status_code = 503
        return {"database": "unconfigured", "alembic_revision": None}

    try:
        async with factory() as session:
            revision = (await session.execute(text("select version_num from alembic_version"))).scalar_one_or_none()
    except Exception as exc:
        # The exception text can contain the DSN with its password. Log the type, return neither.
        log.warning("readiness_check_failed", extra={"error_type": type(exc).__name__})
        response.status_code = 503
        return {"database": "unreachable", "alembic_revision": None}

    return {"database": "ok", "alembic_revision": revision}
