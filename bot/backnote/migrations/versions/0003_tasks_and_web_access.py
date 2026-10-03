"""tasks and web access

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import backnote.db.models

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Web access: login/password + roles. The bot keeps ignoring these columns.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("login", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("can_edit", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_unique_constraint(batch_op.f("uq_users_login"), ["login"])

    op.create_table(
        "web_sessions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column(
            "created_at",
            backnote.db.models.UTCDateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_web_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_sessions")),
    )
    op.create_index("ix_web_sessions_user", "web_sessions", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_tasks_created_by_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"], name=op.f("fk_tasks_lesson_id_lessons"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"], name=op.f("fk_tasks_subject_id_subjects"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )
    op.create_index("ix_tasks_subject_id", "tasks", ["subject_id"])
    op.create_index("ix_tasks_lesson_id", "tasks", ["lesson_id"])

    # A user's personal copy of a task; no row means "use the base version".
    op.create_table(
        "task_work",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_task_work_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name=op.f("fk_task_work_task_id_tasks"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "task_id", name=op.f("pk_task_work")),
    )


def downgrade() -> None:
    op.drop_table("task_work")
    op.drop_index("ix_tasks_lesson_id", table_name="tasks")
    op.drop_index("ix_tasks_subject_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_web_sessions_user", table_name="web_sessions")
    op.drop_table("web_sessions")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("uq_users_login"), type_="unique")
        batch_op.drop_column("can_edit")
        batch_op.drop_column("is_admin")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("login")
