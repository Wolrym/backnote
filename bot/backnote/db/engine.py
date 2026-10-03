from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def ensure_sqlite_dir(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


def normalize_db_url(url: str) -> str:
    if url.startswith("sqlite://") and not url.startswith("sqlite:///"):
        url = "sqlite:///" + url.removeprefix("sqlite://")
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        url = "sqlite+aiosqlite:///" + url.removeprefix("sqlite:///")

    # Якщо шлях відносний (наприклад ../data/backnote.db або data/backnote.db),
    # переконатися, що він веде до єдиної папки data/backnote.db проекту
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        db_path = Path(parsed.database)
        if not db_path.is_absolute():
            # Якщо cwd це корінь web-test-backnote, то data/backnote.db
            # Якщо cwd це bot, то ../data/backnote.db
            if (Path.cwd() / "data" / "backnote.db").exists() or (Path.cwd() / "package.json").exists():
                resolved = (Path.cwd() / "data" / "backnote.db").resolve()
            elif (Path.cwd().parent / "data" / "backnote.db").exists():
                resolved = (Path.cwd().parent / "data" / "backnote.db").resolve()
            else:
                resolved = db_path.resolve()
            url = f"sqlite+aiosqlite:///{resolved.as_posix()}"
    return url


def create_engine(url: str) -> AsyncEngine:
    url = normalize_db_url(url)
    ensure_sqlite_dir(url)
    engine = create_async_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_fk(dbapi_connection, _record) -> None:
            # SQLite ignores ON DELETE CASCADE unless foreign keys are enabled per connection.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
