from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_0036_cancels_only_nonterminal_automatic_ack_work() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0036_cancel_auto_ack_runs.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0036", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    assignments = sa.Table(
        "task_assignments",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assignment_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancellation_reason", sa.String(64)),
    )
    runs = sa.Table(
        "agent_runs",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("lease_token_digest", sa.String(64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("cancellation_reason", sa.String(64)),
    )
    metadata.create_all(engine)
    now = datetime(2026, 9, 3, tzinfo=UTC)
    task_message = uuid4()
    result_sync = uuid4()
    directed = uuid4()
    completed = uuid4()
    rows = [
        (task_message, "task_message", "queued"),
        (result_sync, "result_sync", "running"),
        (directed, "human_directed", "queued"),
        (completed, "task_message", "completed"),
    ]
    with engine.begin() as connection:
        connection.execute(
            assignments.insert(),
            [
                {
                    "id": assignment_id,
                    "assignment_kind": kind,
                    "status": status,
                    "updated_at": now,
                }
                for assignment_id, kind, status in rows
            ],
        )
        connection.execute(
            runs.insert(),
            [
                {
                    "id": uuid4(),
                    "assignment_id": assignment_id,
                    "status": "completed" if status == "completed" else status,
                    "lease_token_digest": "lease" if status == "running" else None,
                    "lease_expires_at": now if status == "running" else None,
                }
                for assignment_id, _, status in rows
            ],
        )
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assignment_state = {
            row.id: (row.status, row.cancellation_reason)
            for row in connection.execute(
                sa.text("SELECT id, status, cancellation_reason FROM task_assignments")
            )
        }
        run_state = {
            row.assignment_id: (row.status, row.cancellation_reason, row.lease_token_digest)
            for row in connection.execute(
                sa.text(
                    "SELECT assignment_id, status, cancellation_reason, lease_token_digest "
                    "FROM agent_runs"
                )
            )
        }

    reason = "automatic_ack_superseded_0_1_46"
    assert assignment_state[task_message.hex] == ("cancelled", reason)
    assert assignment_state[result_sync.hex] == ("cancelled", reason)
    assert run_state[result_sync.hex] == ("cancelled", reason, None)
    assert assignment_state[directed.hex] == ("queued", None)
    assert assignment_state[completed.hex] == ("completed", None)
