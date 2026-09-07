from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_connector_task_listener_migration_round_trip():
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/0040_connector_task_listener_truth.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0040", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "connector_instances",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        migration.op = Operations(
            MigrationContext.configure(connection, opts={"render_as_batch": True})
        )
        migration.upgrade()
        columns = {
            item["name"] for item in sa.inspect(connection).get_columns("connector_instances")
        }
        assert {
            "task_listener_status",
            "task_listener_session_id",
            "task_listener_last_heartbeat_at",
            "wake_capability",
        }.issubset(columns)
        migration.downgrade()
        assert {
            item["name"] for item in sa.inspect(connection).get_columns("connector_instances")
        } == {"id"}
