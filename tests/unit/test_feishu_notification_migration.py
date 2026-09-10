from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _load(name: str):
    path = Path(__file__).resolve().parents[2] / f"migrations/versions/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_feishu_notification_migration_round_trip():
    wake = _load("0041_feishu_aily_wake_channels")
    notification = _load("0042_feishu_human_notifications")
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
        context = MigrationContext.configure(connection)
        wake.op = Operations(context)
        notification.op = Operations(context)
        wake.upgrade()
        notification.upgrade()
        columns = {
            item["name"]: item for item in sa.inspect(connection).get_columns("agent_wake_channels")
        }
        assert columns["connector_instance_id"]["nullable"] is True
        checks = {
            item["name"]: item["sqltext"]
            for item in sa.inspect(connection).get_check_constraints("agent_wake_channels")
        }
        assert "feishu_notification_webhook" in checks["ck_agent_wake_channels_type"]

        notification.downgrade()
        columns = {
            item["name"]: item for item in sa.inspect(connection).get_columns("agent_wake_channels")
        }
        assert columns["connector_instance_id"]["nullable"] is False
        checks = {
            item["name"]: item["sqltext"]
            for item in sa.inspect(connection).get_check_constraints("agent_wake_channels")
        }
        assert "feishu_notification_webhook" not in checks["ck_agent_wake_channels_type"]

        notification.upgrade()
        assert {
            item["name"] for item in sa.inspect(connection).get_columns("agent_wake_channels")
        } >= {"connector_instance_id", "channel_type"}
