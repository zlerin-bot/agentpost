"""Add Human-confirmed semantic relations between immutable task activities.

Revision ID: 0037_task_activity_relations
Revises: 0036_cancel_auto_ack_runs
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0037_task_activity_relations"
down_revision: str | None = "0036_cancel_auto_ack_runs"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "task_activity_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("child_activity_id", sa.Uuid(), nullable=False),
        sa.Column("parent_activity_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("confirmed_by_human_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "child_activity_id <> parent_activity_id",
            name="ck_task_activity_relations_distinct_activities",
        ),
        sa.CheckConstraint(
            "relation_type IN ('reply', 'dismissed_reply_suggestion')",
            name="ck_task_activity_relations_type",
        ),
        sa.CheckConstraint(
            "source IN ('human_confirmed')",
            name="ck_task_activity_relations_source",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_activity_id"], ["task_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_activity_id"], ["task_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["confirmed_by_human_user_id"], ["human_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "child_activity_id",
            "relation_type",
            name="uq_task_activity_relations_child_type",
        ),
    )
    op.create_index(
        "ix_task_activity_relations_task_id",
        "task_activity_relations",
        ["task_id"],
    )
    op.create_index(
        "ix_task_activity_relations_child_activity_id",
        "task_activity_relations",
        ["child_activity_id"],
    )
    op.create_index(
        "ix_task_activity_relations_parent_activity_id",
        "task_activity_relations",
        ["parent_activity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_activity_relations_parent_activity_id",
        table_name="task_activity_relations",
    )
    op.drop_index(
        "ix_task_activity_relations_child_activity_id",
        table_name="task_activity_relations",
    )
    op.drop_index(
        "ix_task_activity_relations_task_id",
        table_name="task_activity_relations",
    )
    op.drop_table("task_activity_relations")
