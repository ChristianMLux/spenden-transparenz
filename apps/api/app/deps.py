"""Request-scoped dependencies.

The engine lives on app.state for the process lifetime. Creating one per request would open a new
connection pool per request, which is the most expensive possible way to run a read-only API.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """A read-only session per request. Rolled back on the way out: nothing here writes."""
    factory = request.app.state.sessionmaker
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
