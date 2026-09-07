"""Record Task listener evidence separately from transport heartbeats."""

import sqlalchemy as sa
from alembic import op

revision = "0040_connector_task_listener_truth"
down_revision = "0039_task_activity_sequence"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("connector_instances") as batch:
        batch.add_column(sa.Column("task_listener_status", sa.String(24), nullable=True))
        batch.add_column(sa.Column("task_listener_session_id", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("task_listener_last_heartbeat_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "wake_capability",
                sa.String(24),
                nullable=False,
                server_default="unsupported",
            )
        )
        batch.create_index(
            "ix_connector_instances_task_listener_last_heartbeat_at",
            ["task_listener_last_heartbeat_at"],
        )
        batch.create_check_constraint(
            "ck_connector_instances_task_listener_status",
            "task_listener_status IS NULL OR task_listener_status IN "
            "('listening', 'stopped', 'error')",
        )
        batch.create_check_constraint(
            "ck_connector_instances_wake_capability",
            "wake_capability IN ('unsupported', 'manual', 'automatic')",
        )


def downgrade():
    with op.batch_alter_table("connector_instances") as batch:
        batch.drop_constraint("ck_connector_instances_wake_capability", type_="check")
        batch.drop_constraint("ck_connector_instances_task_listener_status", type_="check")
        batch.drop_index("ix_connector_instances_task_listener_last_heartbeat_at")
        batch.drop_column("wake_capability")
        batch.drop_column("task_listener_last_heartbeat_at")
        batch.drop_column("task_listener_session_id")
        batch.drop_column("task_listener_status")
