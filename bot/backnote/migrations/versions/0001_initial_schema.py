"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-24 22:37:40.805939
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import backnote.db.models

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notify_new_content", sa.Boolean(), nullable=False),
        sa.Column("notify_deadlines", sa.Boolean(), nullable=False),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column("last_seen_at", backnote.db.models.UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("instructor", sa.String(length=256), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("term", sa.Integer(), nullable=True),
        sa.Column("ects", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_subjects_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
    )
    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_subjects_kind"), ["kind"], unique=False)

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(length=1024), nullable=True),
        sa.Column("held_on", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_source", sa.String(length=16), nullable=True),
        sa.Column("summary_updated_at", backnote.db.models.UTCDateTime(), nullable=True),
        sa.Column("summary_by", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_lessons_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_lessons_subject_id_subjects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["summary_by"],
            ["users.id"],
            name=op.f("fk_lessons_summary_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lessons")),
    )
    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_lessons_subject_id"), ["subject_id"], unique=False)

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("due_at", backnote.db.models.UTCDateTime(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_assignments_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_assignments_lesson_id_lessons"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_assignments_subject_id_subjects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    with op.batch_alter_table("assignments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_assignments_due_at"), ["due_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_assignments_subject_id"), ["subject_id"], unique=False)

    op.create_table(
        "lesson_notes",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("updated_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_notes_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_lesson_notes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "lesson_id", name=op.f("pk_lesson_notes")),
    )
    op.create_table(
        "lesson_progress",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_progress_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_lesson_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "lesson_id", name=op.f("pk_lesson_progress")),
    )
    op.create_table(
        "assignment_progress",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("done_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_assignment_progress_assignment_id_assignments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_assignment_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "assignment_id", name=op.f("pk_assignment_progress")),
    )
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("file_id", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_materials_assignment_id_assignments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_materials_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_materials_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_materials_subject_id_subjects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materials")),
    )
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_materials_assignment_id"), ["assignment_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_materials_lesson_id"), ["lesson_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_materials_subject_id"), ["subject_id"], unique=False)

    op.create_table(
        "reminder_log",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("sent_at", backnote.db.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_reminder_log_assignment_id_assignments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reminder_log_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "assignment_id", "kind", name=op.f("pk_reminder_log")),
    )


def downgrade() -> None:
    op.drop_table("reminder_log")
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_materials_subject_id"))
        batch_op.drop_index(batch_op.f("ix_materials_lesson_id"))
        batch_op.drop_index(batch_op.f("ix_materials_assignment_id"))

    op.drop_table("materials")
    op.drop_table("assignment_progress")
    op.drop_table("lesson_progress")
    op.drop_table("lesson_notes")
    with op.batch_alter_table("assignments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assignments_subject_id"))
        batch_op.drop_index(batch_op.f("ix_assignments_due_at"))

    op.drop_table("assignments")
    with op.batch_alter_table("lessons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lessons_subject_id"))

    op.drop_table("lessons")
    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subjects_kind"))

    op.drop_table("subjects")
    op.drop_table("users")
