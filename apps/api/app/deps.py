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
from limits import parse
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
    # Bytes, not str: secrets.compare_digest raises TypeError on a str holding any non-ASCII
    # character, and headers arrive decoded as latin-1, so one accented byte in the header turned
    # this guard into an unhandled 500 - falsifying the "always 401, never a distinct status"
    # invariant above, in the function protecting the only write route. Encoding cannot fail, and
    # compare_digest stays constant-time over bytes.
    if not secrets.compare_digest((x_admin_token or "").encode("utf-8"), expected.encode("utf-8")) or not expected:
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
#
# Every line, not the first one. X-Forwarded-For is a list header, and RFC 7230 section 3.2.2
# makes two header lines exactly equivalent to one comma-joined line - but Starlette's
# headers.get() returns only the first. Reading the rightmost entry of that line reads the last
# element of the CALLER's own line, which is the same bypass reached through a header shape the
# fix above did not consider: send "X-Forwarded-For: 1.1.1.1" as a second line and rotate it.
# uvicorn's own proxy-headers middleware joins all values before parsing; so does this.


def rate_limit_key(request: Request) -> str:
    forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if hops:
        return hops[-1]
    return request.client.host if request.client else "unknown"


GET_LIMIT = "60/minute"
ADMIN_LIMIT = "5/minute"

limiter = Limiter(key_func=rate_limit_key)

# The read limit is a dependency, not the limiter's default_limits, because SlowAPIMiddleware
# cannot enforce anything in this application. It resolves the handler with
# `route.matches(scope)` + `hasattr(route, "endpoint")`, and this FastAPI version wraps an
# included router in an _IncludedRouter object that matches FULL but carries no `endpoint`
# attribute. slowapi therefore finds no handler, and a request with no handler is treated as
# EXEMPT - so the middleware was silently passing every request through. The admin limit worked
# only because a route decorator is checked inside the endpoint, never through the middleware.
#
# Measured before this fix: 61 consecutive GETs to /v1/meta/enums, all 200.
#
# The check uses the same slowapi Limiter object and therefore the same storage, so
# `limiter.reset()` still clears it and the admin decorator and this share one view of a caller.
_GET_RATE = parse(GET_LIMIT)


async def enforce_get_rate_limit(request: Request) -> None:
    """60/minute per caller on the public read routes.

    Applied to the v1 routers at include time rather than route by route: a read route added later
    inherits the limit by being mounted, instead of by someone remembering a decorator. /health is
    deliberately outside this - see routers/health.py.
    """
    if not limiter.enabled:
        return
    if not limiter.limiter.hit(_GET_RATE, "v1-read", rate_limit_key(request)):
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(_GET_RATE.get_expiry()), "Cache-Control": NO_STORE},
        )
