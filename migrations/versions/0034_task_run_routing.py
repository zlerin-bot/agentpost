"""Add explicit task Run routing and local wakeup evidence.

Revision ID: 0034_task_run_routing
Revises: 0033_connector_runtime_truth
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0034_task_run_routing"
down_revision: str | None = "0033_connector_runtime_truth"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_constraint("ck_task_assignments_kind", type_="check")
        batch.add_column(sa.Column("source_message_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal")
        )
        batch.create_check_constraint(
            "ck_task_assignments_priority",
            "priority IN ('low', 'normal', 'high', 'urgent')",
        )
        batch.create_check_constraint(
            "ck_task_assignments_kind",
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync', "
            "'task_message', 'revision')",
        )
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("local_session_id", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("session_mapped_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("woken_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("result_idempotency_key", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("result_request_hash", sa.String(length=64), nullable=True))
        batch.create_unique_constraint(
            "uq_agent_runs_agent_result_idempotency",
            ["agent_id", "result_idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_constraint("uq_agent_runs_agent_result_idempotency", type_="unique")
        batch.drop_column("result_request_hash")
        batch.drop_column("result_idempotency_key")
        batch.drop_column("woken_at")
        batch.drop_column("session_mapped_at")
        batch.drop_column("local_session_id")
        batch.drop_column("claimed_at")
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_constraint("ck_task_assignments_kind", type_="check")
        batch.drop_constraint("ck_task_assignments_priority", type_="check")
        batch.drop_column("priority")
        batch.drop_column("source_message_id")
        batch.create_check_constraint(
            "ck_task_assignments_kind",
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync', "
            "'task_message')",
        )
