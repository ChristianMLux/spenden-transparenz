"""Alembic environment.

Deliberately synchronous, on the psycopg driver: the application is async, but migrations gain
nothing from an event loop and lose transactional simplicity. core.settings derives the sync URL
from DATABASE_URL, or takes DATABASE_URL_SYNC when it is set explicitly.

alembic.ini leaves sqlalchemy.url empty on purpose, so a stale URL committed to a file can never be
picked up by accident. A caller may still set it programmatically (the migration tests do, to run
against a scratch database).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from core.models import Base
from core.settings import get_settings
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    configured = config.get_main_option("sqlalchemy.url", default="")
    return configured or get_settings().sync_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Both are needed for `alembic check` to be meaningful: without them a changed column
            # type or server default would not show up as a pending migration.
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
