"""Cancel nonterminal automatic acknowledgement Runs superseded by shared context.

Revision ID: 0036_cancel_auto_ack_runs
Revises: 0035_cancel_legacy_task_backlog
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0036_cancel_auto_ack_runs"
down_revision: str | None = "0035_cancel_legacy_task_backlog"
branch_labels: str | None = None
depends_on: str | None = None

CANCELLATION_REASON = "automatic_ack_superseded_0_1_46"


def upgrade() -> None:
    bind = op.get_bind()
    cleanup_at = datetime.now(UTC)
    assignments = sa.table(
        "task_assignments",
        sa.column("id", sa.Uuid()),
        sa.column("assignment_kind", sa.String()),
        sa.column("status", sa.String()),
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
        assignments.c.assignment_kind.in_(["task_message", "result_sync"]),
        assignments.c.status.in_(["queued", "running", "waiting_human"]),
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
    # Never revive acknowledgement Runs during rollback; the history remains readable.
    return
