"""Track the runtime version reported by current Connector heartbeats.

Revision ID: 0028_connector_runtime_versions
Revises: 0027_tasks
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_connector_runtime_versions"
down_revision: str | None = "0027_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "connector_instances",
        sa.Column("runtime_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "connector_instances",
        sa.Column("runtime_version_reported_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("connector_instances", "runtime_version_reported_at")
    op.drop_column("connector_instances", "runtime_version")
