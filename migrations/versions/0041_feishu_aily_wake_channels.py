"""Add durable Feishu aily webhook wake channels and delivery receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0041_feishu_aily_wake_channels"
down_revision = "0040_connector_task_listener_truth"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_wake_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("human_user_id", sa.Uuid(), nullable=False),
        sa.Column("connector_instance_id", sa.Uuid(), nullable=False),
        sa.Column("channel_type", sa.String(40), nullable=False),
        sa.Column("encrypted_endpoint", sa.Text(), nullable=False),
        sa.Column("encrypted_bearer_token", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "channel_type IN ('feishu_aily_webhook')",
            name="ck_agent_wake_channels_type",
        ),
        sa.CheckConstraint(
            "status IN ('configured', 'active', 'error', 'disabled')",
            name="ck_agent_wake_channels_status",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["human_user_id"], ["human_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["connector_instance_id"], ["connector_instances.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agent_wake_channels_agent"),
    )
    op.create_table(
        "agent_wake_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'delivered', 'failed', 'cancelled')",
            name="ck_agent_wake_deliveries_status",
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["agent_wake_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["task_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_agent_wake_deliveries_run"),
    )
    op.create_index("ix_agent_wake_deliveries_status", "agent_wake_deliveries", ["status"])
    op.create_index(
        "ix_agent_wake_deliveries_available_at",
        "agent_wake_deliveries",
        ["available_at"],
    )


def downgrade():
    op.drop_index("ix_agent_wake_deliveries_available_at", table_name="agent_wake_deliveries")
    op.drop_index("ix_agent_wake_deliveries_status", table_name="agent_wake_deliveries")
    op.drop_table("agent_wake_deliveries")
    op.drop_table("agent_wake_channels")
