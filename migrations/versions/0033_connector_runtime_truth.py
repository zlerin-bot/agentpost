"""Record installed, configured, and actually loaded Connector versions.

Revision ID: 0033_connector_runtime_truth
Revises: 0032_task_only_collaboration
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0033_connector_runtime_truth"
down_revision: str | None = "0032_task_only_collaboration"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("connector_instances") as batch:
        batch.add_column(sa.Column("installed_version", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("configured_version", sa.String(length=100), nullable=True))
        batch.add_column(
            sa.Column("runtime_session_started_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("connector_instances") as batch:
        batch.drop_column("runtime_session_started_at")
        batch.drop_column("configured_version")
        batch.drop_column("installed_version")
