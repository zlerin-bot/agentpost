"""Separate Human Feishu notifications from Aily Agent wakeups."""

import sqlalchemy as sa
from alembic import op

revision = "0042_feishu_human_notifications"
down_revision = "0041_feishu_aily_wake_channels"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("agent_wake_channels") as batch:
        batch.drop_constraint("ck_agent_wake_channels_type", type_="check")
        batch.alter_column("connector_instance_id", existing_type=sa.Uuid(), nullable=True)
        batch.create_check_constraint(
            "ck_agent_wake_channels_type",
            "channel_type IN ('feishu_aily_webhook', 'feishu_notification_webhook')",
        )


def downgrade():
    op.execute("DELETE FROM agent_wake_channels WHERE channel_type = 'feishu_notification_webhook'")
    with op.batch_alter_table("agent_wake_channels") as batch:
        batch.drop_constraint("ck_agent_wake_channels_type", type_="check")
        batch.alter_column("connector_instance_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_check_constraint(
            "ck_agent_wake_channels_type",
            "channel_type IN ('feishu_aily_webhook')",
        )
