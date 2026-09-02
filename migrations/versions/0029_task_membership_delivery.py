"""Activate task members with default Agents and track email notification state.

Revision ID: 0029_task_membership_delivery
Revises: 0028_connector_runtime_versions
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_task_membership_delivery"
down_revision: str | None = "0028_connector_runtime_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("agent_creation_key", sa.String(length=255), nullable=True))
        batch.create_unique_constraint(
            "uq_tasks_agent_creation_key", ["coordinator_agent_id", "agent_creation_key"]
        )
    with op.batch_alter_table("task_memberships") as batch:
        batch.add_column(
            sa.Column(
                "agent_selection_source",
                sa.String(length=16),
                nullable=False,
                server_default="selected",
            )
        )
        batch.add_column(
            sa.Column(
                "email_notification_status",
                sa.String(length=16),
                nullable=False,
                server_default="not_applicable",
            )
        )
        batch.add_column(
            sa.Column(
                "email_notification_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(sa.Column("email_notified_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint(
            "ck_task_memberships_agent_selection_source",
            "agent_selection_source IN ('selected', 'default')",
        )
        batch.create_check_constraint(
            "ck_task_memberships_email_notification_status",
            "email_notification_status IN ('not_applicable', 'pending', 'sent', 'failed')",
        )
    with op.batch_alter_table("task_assignments") as batch:
        batch.add_column(
            sa.Column(
                "assignment_kind",
                sa.String(length=32),
                nullable=False,
                server_default="human_directed",
            )
        )
        batch.add_column(sa.Column("trigger_activity_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_task_assignments_trigger_activity",
            "task_activities",
            ["trigger_activity_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint(
            "uq_task_assignments_agent_trigger",
            ["assignee_agent_id", "trigger_activity_id"],
        )
        batch.create_check_constraint(
            "ck_task_assignments_kind",
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync')",
        )


def downgrade() -> None:
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_constraint("ck_task_assignments_kind", type_="check")
        batch.drop_constraint("uq_task_assignments_agent_trigger", type_="unique")
        batch.drop_constraint("fk_task_assignments_trigger_activity", type_="foreignkey")
        batch.drop_column("trigger_activity_id")
        batch.drop_column("assignment_kind")
    with op.batch_alter_table("task_memberships") as batch:
        batch.drop_constraint("ck_task_memberships_email_notification_status", type_="check")
        batch.drop_constraint("ck_task_memberships_agent_selection_source", type_="check")
        batch.drop_column("email_notified_at")
        batch.drop_column("email_notification_attempts")
        batch.drop_column("email_notification_status")
        batch.drop_column("agent_selection_source")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("uq_tasks_agent_creation_key", type_="unique")
        batch.drop_column("agent_creation_key")
