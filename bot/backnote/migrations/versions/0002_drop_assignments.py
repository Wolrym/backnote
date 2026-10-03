"""drop assignments

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24 23:26:06.885761
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # materials must lose its FK before "assignments" disappears: batch mode reflects referents.
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_materials_assignment_id"))
        batch_op.drop_constraint(
            batch_op.f("fk_materials_assignment_id_assignments"), type_="foreignkey"
        )
        batch_op.drop_column("assignment_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("notify_deadlines")

    op.drop_table("reminder_log")
    op.drop_table("assignment_progress")
    op.drop_index(op.f("ix_assignments_due_at"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_subject_id"), table_name="assignments")
    op.drop_table("assignments")


def downgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("subject_id", sa.INTEGER(), nullable=False),
        sa.Column("lesson_id", sa.INTEGER(), nullable=True),
        sa.Column("title", sa.VARCHAR(length=256), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("url", sa.VARCHAR(length=1024), nullable=True),
        sa.Column("due_at", sa.DATETIME(), nullable=True),
        sa.Column("created_by", sa.BIGINT(), nullable=True),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.Column("updated_at", sa.DATETIME(), nullable=False),
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
        batch_op.create_index(batch_op.f("ix_assignments_subject_id"), ["subject_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_assignments_due_at"), ["due_at"], unique=False)

    op.create_table(
        "assignment_progress",
        sa.Column("user_id", sa.BIGINT(), nullable=False),
        sa.Column("assignment_id", sa.INTEGER(), nullable=False),
        sa.Column("done_at", sa.DATETIME(), nullable=False),
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
        "reminder_log",
        sa.Column("user_id", sa.BIGINT(), nullable=False),
        sa.Column("assignment_id", sa.INTEGER(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("sent_at", sa.DATETIME(), nullable=False),
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

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("notify_deadlines", sa.BOOLEAN(), nullable=False, server_default=sa.true())
        )

    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.add_column(sa.Column("assignment_id", sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_materials_assignment_id_assignments"),
            "assignments",
            ["assignment_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            batch_op.f("ix_materials_assignment_id"), ["assignment_id"], unique=False
        )
