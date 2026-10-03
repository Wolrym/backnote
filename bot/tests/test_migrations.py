import sqlite3
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from backnote.db.migrate import upgrade
from backnote.db.models import Base


def test_migrations_match_models(db_url: str):
    sync_url = db_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], f"Models changed without a migration: {diff}"


def test_dropping_assignments_keeps_existing_data(tmp_path: Path):
    path = tmp_path / "old.db"
    url = f"sqlite+aiosqlite:///{path}"
    upgrade(url, "0001")
    con = sqlite3.connect(path)
    con.executescript(
        """
        INSERT INTO users (id, status, notify_new_content, notify_deadlines, created_at)
            VALUES (1, 'active', 1, 1, '2026-01-01');
        INSERT INTO subjects (id, kind, title, is_archived, created_at, updated_at)
            VALUES (1, 'subject', 'OOP', 0, '2026-01-01', '2026-01-01');
        INSERT INTO lessons (id, subject_id, number, kind, title, created_at, updated_at)
            VALUES (1, 1, 1, 'lecture', 'Intro', '2026-01-01', '2026-01-01');
        INSERT INTO lesson_progress VALUES (1, 1, '2026-01-01');
        INSERT INTO lesson_notes VALUES (1, 1, 'note', '2026-01-01');
        INSERT INTO materials (subject_id, lesson_id, kind, title, created_at)
            VALUES (1, 1, 'link', 'slides', '2026-01-01');
        """
    )
    con.commit()
    con.close()

    upgrade(url)

    con = sqlite3.connect(path)
    counts = [
        con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("users", "lesson_progress", "lesson_notes", "materials")
    ]
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert counts == [1, 1, 1, 1]
    assert "assignments" not in tables
