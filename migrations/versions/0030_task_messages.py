"""Add idempotent task messages and task-message assignments.

Revision ID: 0030_task_messages
Revises: 0029_task_membership_delivery
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_task_messages"
down_revision: str | None = "0029_task_membership_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("connector_instances") as batch:
        batch.add_column(
            sa.Column(
                "runtime_capabilities",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
    with op.batch_alter_table("task_activities") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("request_hash", sa.String(length=64), nullable=True))
        batch.create_unique_constraint(
            "uq_task_activities_agent_idempotency",
            ["actor_agent_id", "idempotency_key"],
        )
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_constraint("ck_task_assignments_kind", type_="check")
        batch.create_check_constraint(
            "ck_task_assignments_kind",
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync', "
            "'task_message')",
        )


def downgrade() -> None:
    op.execute(
        "UPDATE task_assignments SET assignment_kind = 'result_sync' "
        "WHERE assignment_kind = 'task_message'"
    )
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_constraint("ck_task_assignments_kind", type_="check")
        batch.create_check_constraint(
            "ck_task_assignments_kind",
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync')",
        )
    with op.batch_alter_table("task_activities") as batch:
        batch.drop_constraint("uq_task_activities_agent_idempotency", type_="unique")
        batch.drop_column("request_hash")
        batch.drop_column("idempotency_key")
    with op.batch_alter_table("connector_instances") as batch:
        batch.drop_column("runtime_capabilities")
