"""Engine and session factory.

One engine per process, created at startup and disposed at shutdown. Creating an engine per
request would open a new connection pool per request, which is the most expensive way to run a
read-only API.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def make_engine(url: str, *, echo: bool = False, pool_size: int = 5, max_overflow: int = 5) -> AsyncEngine:
    return create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
    )


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
