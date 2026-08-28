"""Request-scoped dependencies.

The engine lives on app.state for the process lifetime. Creating one per request would open a new
connection pool per request, which is the most expensive possible way to run a read-only API.

This module also carries the cross-cutting request concerns that the six routers all need the same
way: the session dependency, the admin-token check, the Cache-Control values from the spec, and the
rate limiter. Putting them in one place means the six routers cannot each invent a slightly
different answer to "how is this endpoint protected."
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator

from core.settings import get_settings
from fastapi import Header, HTTPException, Request, Response
from slowapi import Limiter
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """A read-only session per request. Rolled back on the way out: nothing here writes."""
    factory = request.app.state.sessionmaker
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


# --- Name search -------------------------------------------------------------------------------

ILIKE_ESCAPE = "\\"


def ilike_pattern(q: str) -> str:
    """Turn free-text search input into a literal ILIKE pattern, wrapped in wildcards.

    ILIKE treats "%" and "_" in the search text itself as wildcards - not just an injection risk
    (this is parameterised, never string-formatted SQL), but a correctness one: an unescaped
    q="%" would match every organisation. Escaping them (and the escape character itself, first)
    makes the search behave like a literal substring match, which is what "search by name" means.
    """
    escaped = q.replace(ILIKE_ESCAPE, ILIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


# --- Cache-Control ---------------------------------------------------------------------------
#
# One dependency per cache tier, not a global guess: list endpoints refresh often (a new
# statement can land any hour), an organisation page changes rarely, and reference data (meta)
# barely ever. Each router opts into the tier that matches what it serves.

LIST_CACHE = "public, max-age=60, stale-while-revalidate=600"
DETAIL_CACHE = "public, max-age=300"
META_CACHE = "public, max-age=3600"
NO_STORE = "no-store"


def list_cache(response: Response) -> None:
    response.headers["Cache-Control"] = LIST_CACHE


def detail_cache(response: Response) -> None:
    response.headers["Cache-Control"] = DETAIL_CACHE


def meta_cache(response: Response) -> None:
    response.headers["Cache-Control"] = META_CACHE


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = NO_STORE


# --- Admin token -------------------------------------------------------------------------------


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Constant-time comparison. No configured token means closed, never open.

    Always 401, never a distinct status for "no token is configured": that would tell an
    unauthenticated caller which deployments have an unset ADMIN_TOKEN. Production cannot reach
    that state anyway - core.settings refuses to start without one.

    secrets.compare_digest runs on both branches: an early return for "no token configured" would
    leak the same fact through timing that the status code is hiding.

    The Cache-Control header is set directly on the raised exception, not through the no_store
    dependency: FastAPI builds an entirely new response for an HTTPException rather than reusing
    the Response object dependencies mutate, so a 401 would otherwise ship with no Cache-Control
    header at all.
    """
    configured = get_settings().admin_token
    expected = configured.get_secret_value() if configured is not None else ""
    if not secrets.compare_digest(x_admin_token or "", expected) or not expected:
        raise HTTPException(status_code=401, detail="invalid admin token", headers={"Cache-Control": NO_STORE})


# --- Rate limiting -------------------------------------------------------------------------------
#
# X-Forwarded-For reads left to right as "client, proxy1, proxy2, ...": each hop APPENDS the
# address it received the request from, so the client's own value - real or invented - always
# comes first. Railway terminates TLS and is this API's only ingress, so the LAST entry is the one
# Railway itself appended: the address it actually observed the connection from, which a caller
# cannot forge no matter how many fake entries they prepend or how often they rotate them. This is
# correct whether Railway appends to an existing header or replaces it outright, so it does not
# depend on verifying Railway's exact proxy behaviour. Trusting the first hop instead - the
# original mistake here - lets a caller get a fresh rate-limit bucket on every request just by
# sending a different X-Forwarded-For value, defeating the 5/min admin limit entirely.


def rate_limit_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=rate_limit_key)

GET_LIMIT = "60/minute"
ADMIN_LIMIT = "5/minute"
