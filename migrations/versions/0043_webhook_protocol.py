"""Explicit webhook authentication and durable dispatch cooldown."""

import sqlalchemy as sa
from alembic import op

revision = "0043_webhook_protocol"
down_revision = "0042_feishu_human_notifications"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("agent_wake_channels") as batch:
        batch.add_column(
            sa.Column("auth_scheme", sa.String(20), nullable=False, server_default="bearer")
        )
        batch.add_column(sa.Column("last_dispatch_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("agent_wake_channels") as batch:
        batch.drop_column("last_dispatch_at")
        batch.drop_column("auth_scheme")
