import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from backnote.db.engine import ensure_sqlite_dir
from backnote.db.models import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    url = (
        config.get_main_option("sqlalchemy.url")
        or os.environ.get("DATABASE_URL")
        or "sqlite+aiosqlite:///data/backnote.db"
    )
    if url.startswith("sqlite://") and not url.startswith("sqlite:///"):
        url = "sqlite:///" + url.removeprefix("sqlite://")
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        url = "sqlite+aiosqlite:///" + url.removeprefix("sqlite:///")
    return url


def _configure(**kwargs) -> None:
    # Batch mode lets Alembic emulate ALTER TABLE on SQLite.
    context.configure(target_metadata=target_metadata, render_as_batch=True, **kwargs)


def run_offline() -> None:
    _configure(url=database_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    # Deliberately without the foreign_keys pragma: batch migrations recreate tables on SQLite,
    # and with FKs on, dropping the old table would cascade-delete dependent rows.
    ensure_sqlite_dir(database_url())
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
