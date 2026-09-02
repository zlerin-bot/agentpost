"""Cancel obsolete pre-0.1.44 automatically generated Task Run backlog.

Revision ID: 0035_cancel_legacy_task_backlog
Revises: 0034_task_run_routing
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0035_cancel_legacy_task_backlog"
down_revision: str | None = "0034_task_run_routing"
branch_labels: str | None = None
depends_on: str | None = None

LEGACY_CUTOFF = datetime(2026, 9, 2, 15, 31, 43, tzinfo=UTC)
CANCELLATION_REASON = "legacy_pre_0_1_44_backlog"


def upgrade() -> None:
    with op.batch_alter_table("task_assignments") as batch:
        batch.add_column(sa.Column("cancellation_reason", sa.String(length=64), nullable=True))
    with op.batch_alter_table("agent_runs") as batch:
        batch.add_column(sa.Column("cancellation_reason", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    cleanup_at = datetime.now(UTC)
    assignments = sa.table(
        "task_assignments",
        sa.column("id", sa.Uuid()),
        sa.column("assignment_kind", sa.String()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("completed_at", sa.DateTime(timezone=True)),
        sa.column("cancellation_reason", sa.String()),
    )
    runs = sa.table(
        "agent_runs",
        sa.column("assignment_id", sa.Uuid()),
        sa.column("status", sa.String()),
        sa.column("lease_token_digest", sa.String()),
        sa.column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.column("finished_at", sa.DateTime(timezone=True)),
        sa.column("error_code", sa.String()),
        sa.column("cancellation_reason", sa.String()),
    )
    obsolete_assignment_ids = sa.select(assignments.c.id).where(
        assignments.c.assignment_kind.in_(["participant_start", "task_message", "result_sync"]),
        assignments.c.status.in_(["queued", "running", "waiting_human"]),
        assignments.c.created_at < LEGACY_CUTOFF,
    )
    bind.execute(
        sa.update(runs)
        .where(
            runs.c.assignment_id.in_(obsolete_assignment_ids),
            runs.c.status.in_(
                ["queued", "leased", "starting", "running", "waiting_human", "interrupted"]
            ),
        )
        .values(
            status="cancelled",
            lease_token_digest=None,
            lease_expires_at=None,
            finished_at=cleanup_at,
            error_code=CANCELLATION_REASON,
            cancellation_reason=CANCELLATION_REASON,
        )
    )
    bind.execute(
        sa.update(assignments)
        .where(assignments.c.id.in_(obsolete_assignment_ids))
        .values(
            status="cancelled",
            updated_at=cleanup_at,
            completed_at=cleanup_at,
            cancellation_reason=CANCELLATION_REASON,
        )
    )


def downgrade() -> None:
    # Status cancellation is intentionally durable: restoring obsolete queued
    # work during a rollback could wake Agents and repeat old collaboration.
    with op.batch_alter_table("agent_runs") as batch:
        batch.drop_column("cancellation_reason")
    with op.batch_alter_table("task_assignments") as batch:
        batch.drop_column("cancellation_reason")
