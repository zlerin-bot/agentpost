from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load_migration():
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0035_cancel_legacy_task_backlog.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0035", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_0035_cancels_only_obsolete_automatic_backlog() -> None:
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    assignments = sa.Table(
        "task_assignments",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assignment_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
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
    )
    metadata.create_all(engine)

    old_automatic = uuid4()
    old_human = uuid4()
    new_automatic = uuid4()
    old_completed = uuid4()
    old_time = datetime(2026, 9, 1, tzinfo=UTC)
    new_time = datetime(2026, 9, 3, tzinfo=UTC)
    rows = [
        (old_automatic, "task_message", "queued", old_time),
        (old_human, "human_directed", "queued", old_time),
        (new_automatic, "participant_start", "queued", new_time),
        (old_completed, "result_sync", "completed", old_time),
    ]

    with engine.begin() as connection:
        connection.execute(
            assignments.insert(),
            [
                {
                    "id": assignment_id,
                    "assignment_kind": kind,
                    "status": status,
                    "created_at": created_at,
                    "updated_at": created_at,
                }
                for assignment_id, kind, status, created_at in rows
            ],
        )
        connection.execute(
            runs.insert(),
            [
                {
                    "id": uuid4(),
                    "assignment_id": assignment_id,
                    "status": "completed" if status == "completed" else "queued",
                    "lease_token_digest": "lease" if assignment_id == old_automatic else None,
                    "lease_expires_at": old_time if assignment_id == old_automatic else None,
                }
                for assignment_id, _, status, _ in rows
            ],
        )

        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        assignment_state = {
            row.id: (row.status, row.cancellation_reason)
            for row in connection.execute(
                sa.text("SELECT id, status, cancellation_reason FROM task_assignments")
            )
        }
        run_state = {
            row.assignment_id: (
                row.status,
                row.cancellation_reason,
                row.lease_token_digest,
            )
            for row in connection.execute(
                sa.text(
                    "SELECT assignment_id, status, cancellation_reason, lease_token_digest "
                    "FROM agent_runs"
                )
            )
        }

    reason = "legacy_pre_0_1_44_backlog"
    assert assignment_state[old_automatic.hex] == ("cancelled", reason)
    assert run_state[old_automatic.hex] == ("cancelled", reason, None)
    assert assignment_state[old_human.hex] == ("queued", None)
    assert assignment_state[new_automatic.hex] == ("queued", None)
    assert assignment_state[old_completed.hex] == ("completed", None)
