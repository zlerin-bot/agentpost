from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_personal_task_migration_round_trip():
    path = (
        Path(__file__).resolve().parents[2] / "migrations/versions/0038_human_task_preferences.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0038", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert "human_task_preferences" in sa.inspect(connection).get_table_names()
        migration.downgrade()
        assert "human_task_preferences" not in sa.inspect(connection).get_table_names()
        migration.upgrade()
        assert {
            c["name"] for c in sa.inspect(connection).get_columns("human_task_preferences")
        } == {"human_user_id", "task_id", "list_state", "seen_activity_ids"}
