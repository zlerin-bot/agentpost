from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_feishu_aily_wake_migration_round_trip():
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/0041_feishu_aily_wake_channels.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0041", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    for name in (
        "agents",
        "human_users",
        "connector_instances",
        "tasks",
        "task_assignments",
        "agent_runs",
    ):
        sa.Table(name, metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    metadata.create_all(engine)

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert {
            "agent_wake_channels",
            "agent_wake_deliveries",
        }.issubset(inspector.get_table_names())
        assert {item["name"] for item in inspector.get_indexes("agent_wake_deliveries")} == {
            "ix_agent_wake_deliveries_available_at",
            "ix_agent_wake_deliveries_status",
        }
        migration.downgrade()
        downgraded_tables = sa.inspect(connection).get_table_names()
        assert "agent_wake_channels" not in downgraded_tables
        assert "agent_wake_deliveries" not in downgraded_tables
        migration.upgrade()
        assert {
            "agent_wake_channels",
            "agent_wake_deliveries",
        }.issubset(sa.inspect(connection).get_table_names())
