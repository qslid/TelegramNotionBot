"""Async SQLAlchemy engine / session factory.

Supports SQLite (default) and PostgreSQL via DATABASE_URL.
For PostgreSQL use: postgresql+asyncpg://user:pass@host:5432/dbname
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import get_settings
from bot.database.models import Base

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the live session factory (raises if DB not initialized)."""
    if _session_factory is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return _session_factory


def try_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Return the session factory or None if DB is not ready."""
    return _session_factory


def _normalize_url(url: str) -> str:
    """Ensure SQLite URLs use the aiosqlite driver."""
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def init_db() -> None:
    """Create engine, session factory, and tables."""
    global _engine, _session_factory

    settings = get_settings()
    url = _normalize_url(settings.database_url)

    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose the engine on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession (for DI-style usage)."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
