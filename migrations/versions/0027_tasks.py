"""Add Human friendships and single-Thread Task execution.

Revision ID: 0027_tasks
Revises: 0026_message_attachment_links
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_tasks"
down_revision: str | None = "0026_message_attachment_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "friendships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("human_a_id", sa.Uuid(), nullable=False),
        sa.Column("human_b_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_human_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("human_a_id <> human_b_id", name="ck_friendships_distinct_humans"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'removed')",
            name="ck_friendships_status",
        ),
        sa.ForeignKeyConstraint(["human_a_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["human_b_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_human_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("human_a_id", "human_b_id", name="uq_friendships_human_pair"),
    )
    op.create_index("ix_friendships_status", "friendships", ["status"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_human_user_id", sa.Uuid(), nullable=False),
        sa.Column("coordinator_agent_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("final_summary", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'awaiting_acceptance', 'completed', "
            "'cancelled', 'archived')",
            name="ck_tasks_status",
        ),
        sa.ForeignKeyConstraint(["owner_human_user_id"], ["human_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coordinator_agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
    op.create_index("ix_tasks_owner_human_user_id", "tasks", ["owner_human_user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_thread_id", "tasks", ["thread_id"], unique=True)

    op.create_table(
        "task_memberships",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("human_user_id", sa.Uuid(), nullable=False),
        sa.Column("primary_agent_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'member')", name="ck_task_memberships_role"),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'declined')",
            name="ck_task_memberships_status",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["human_user_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["human_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("task_id", "human_user_id"),
    )
    op.create_index("ix_task_memberships_human_user_id", "task_memberships", ["human_user_id"])

    op.create_table(
        "task_agent_participants",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("human_user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('primary', 'support')", name="ck_task_agents_role"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["human_user_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "agent_id"),
    )

    op.create_table(
        "task_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("responsible_human_user_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_agent_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_human_user_id", sa.Uuid(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_status", sa.String(length=32), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'waiting_human', 'completed', 'partial', "
            "'failed', 'cancelled')",
            name="ck_task_assignments_status",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["responsible_human_user_id"], ["human_users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["assignee_agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["created_by_human_user_id"], ["human_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_assignments_task_id", "task_assignments", ["task_id"])
    op.create_index("ix_task_assignments_agent", "task_assignments", ["assignee_agent_id"])
    op.create_index("ix_task_assignments_status", "task_assignments", ["status"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("lease_token_digest", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'leased', 'starting', 'running', 'waiting_human', "
            "'completed', 'partial', 'failed', 'cancelled', 'interrupted')",
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["task_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "attempt", name="uq_agent_runs_assignment_attempt"),
        sa.UniqueConstraint("lease_token_digest"),
    )
    op.create_index("ix_agent_runs_assignment_id", "agent_runs", ["assignment_id"])
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "task_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_human_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_human_user_id", sa.Uuid(), nullable=True),
        sa.Column("activity_metadata", sa.JSON(), nullable=False),
        sa.Column("security_label", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_human_user_id"], ["human_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_human_user_id"], ["human_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_activities_task_id", "task_activities", ["task_id"])
    op.create_index("ix_task_activities_type", "task_activities", ["activity_type"])
    op.create_index("ix_task_activities_created_at", "task_activities", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_task_activities_created_at", table_name="task_activities")
    op.drop_index("ix_task_activities_type", table_name="task_activities")
    op.drop_index("ix_task_activities_task_id", table_name="task_activities")
    op.drop_table("task_activities")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_assignment_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_task_assignments_status", table_name="task_assignments")
    op.drop_index("ix_task_assignments_agent", table_name="task_assignments")
    op.drop_index("ix_task_assignments_task_id", table_name="task_assignments")
    op.drop_table("task_assignments")
    op.drop_table("task_agent_participants")
    op.drop_index("ix_task_memberships_human_user_id", table_name="task_memberships")
    op.drop_table("task_memberships")
    op.drop_index("ix_tasks_thread_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_owner_human_user_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_friendships_status", table_name="friendships")
    op.drop_table("friendships")
