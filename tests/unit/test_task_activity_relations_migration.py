from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_0037_creates_and_removes_task_activity_relations() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "0037_task_activity_relations.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0037", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table("tasks", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    sa.Table("task_activities", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    sa.Table("human_users", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    metadata.create_all(engine)

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert "task_activity_relations" in inspector.get_table_names()
        assert {
            "ix_task_activity_relations_task_id",
            "ix_task_activity_relations_child_activity_id",
            "ix_task_activity_relations_parent_activity_id",
        }.issubset({item["name"] for item in inspector.get_indexes("task_activity_relations")})
        migration.downgrade()
        assert "task_activity_relations" not in sa.inspect(connection).get_table_names()
