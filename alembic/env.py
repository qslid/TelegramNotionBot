"""Alembic environment — async migrations against bot SQLAlchemy models.

Reads DATABASE_URL from Settings (.env). Normalizes postgres:// and sqlite://
URLs the same way as bot.database.db.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from bot.database.db import _normalize_url
from bot.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Resolve async DB URL from env / .env (BOT_TOKEN not required for migrate)."""
    # Avoid requiring BOT_TOKEN when only migrating: read DATABASE_URL directly.
    import os

    from dotenv import load_dotenv

    load_dotenv()
    raw = os.getenv("DATABASE_URL")
    if not raw:
        # Fall back to Settings default (SQLite) without forcing BOT_TOKEN.
        raw = "sqlite+aiosqlite:///./bot.db"
    return _normalize_url(raw)


def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
