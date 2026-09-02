"""Track deduplicated Connector upgrade directives.

Revision ID: 0031_connector_upgrade_directives
Revises: 0030_task_messages
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_connector_upgrade_directives"
down_revision: str | None = "0030_task_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("connector_instances") as batch:
        batch.add_column(sa.Column("upgrade_target_version", sa.String(length=32)))
        batch.add_column(sa.Column("upgrade_status", sa.String(length=24)))
        batch.add_column(sa.Column("upgrade_requested_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("upgrade_completed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("upgrade_notification_message_id", sa.String(length=64)))
        batch.create_check_constraint(
            "ck_connector_instances_upgrade_status",
            "upgrade_status IS NULL OR upgrade_status IN ('requested', 'completed')",
        )


def downgrade() -> None:
    with op.batch_alter_table("connector_instances") as batch:
        batch.drop_constraint("ck_connector_instances_upgrade_status", type_="check")
        batch.drop_column("upgrade_notification_message_id")
        batch.drop_column("upgrade_completed_at")
        batch.drop_column("upgrade_requested_at")
        batch.drop_column("upgrade_status")
        batch.drop_column("upgrade_target_version")
