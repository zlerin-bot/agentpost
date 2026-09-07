from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_postgres_acceptance import _settings
from test_task_collaboration import _create_owned_agent, _register, _runtime

from agentpost.identity.models import utc_now
from agentpost.main import create_app
from agentpost.tasks.models import TaskActivity
from agentpost.tasks.service import _add_activity

pytestmark = pytest.mark.postgres


def test_committed_cursor_cannot_skip_late_transaction(migrated_database, tmp_path):
    db = migrated_database
    settings = _runtime(_settings(str(db.engine.url), tmp_path))
    with TestClient(create_app(settings=settings, database=db)) as client:
        owner = _register(client, "publication-owner")
        agent = _create_owned_agent(
            client, human_id=owner["user"]["id"], handle="publication-owner"
        )
        auth = {"Authorization": f"Bearer {agent['api_key']}"}
        created = client.post(
            "/api/v1/agent/tasks",
            headers={**auth, "Idempotency-Key": "publication"},
            json={"title": "concurrency", "goal": "no gaps", "expected_output": "proof"},
        )
        assert created.status_code == 201, created.text
        task_id = UUID(created.json()["task_id"])
        url = f"/api/v1/agent/tasks/{task_id}/activities"
        cursor = client.get(url, headers=auth).json()["next_cursor"]
        first_written, second_started, allow_commit = Event(), Event(), Event()

        def first():
            with db.session_factory() as session:
                row = _add_activity(
                    session, task_id=task_id, kind="task_message", actor_type="platform"
                )
                session.flush()
                first_written.set()
                assert allow_commit.wait(10)
                id_ = str(row.id)
                session.commit()
                return id_

        def second():
            second_started.set()
            with db.session_factory() as session:
                row = _add_activity(
                    session, task_id=task_id, kind="task_message", actor_type="platform"
                )
                # Imported/backdated time must never determine publication position.
                row.created_at = utc_now() - timedelta(days=30)
                session.flush()
                id_ = str(row.id)
                session.commit()
                return id_

        with ThreadPoolExecutor(max_workers=2) as executor:
            one = executor.submit(first)
            assert first_written.wait(5)
            two = executor.submit(second)
            assert second_started.wait(5)
            try:
                assert (
                    client.get(url, headers=auth, params={"cursor": cursor}).json()["items"] == []
                )
            finally:
                allow_commit.set()
            ids = [one.result(timeout=10), two.result(timeout=10)]
        page = client.get(url, headers=auth, params={"cursor": cursor, "limit": 1}).json()
        assert [item["activity_id"] for item in page["items"]] == ids[:1]
        page2 = client.get(url, headers=auth, params={"cursor": page["next_cursor"]}).json()
        assert [item["activity_id"] for item in page2["items"]] == ids[1:]
        assert page2["order"] == "task_sequence_asc"
        with db.session_factory() as session:
            rows = session.scalars(
                select(TaskActivity)
                .where(TaskActivity.task_id == task_id)
                .order_by(TaskActivity.sequence)
            ).all()
            assert len({row.sequence for row in rows}) == len(rows)


def test_two_device_views_merge_and_one_run_has_one_claim(migrated_database, tmp_path):
    from threading import Barrier

    from agentpost.control.models import HumanUser
    from agentpost.tasks.preferences import preference_summary, update_preference
    from agentpost.tasks.schemas import TaskPreferenceUpdate

    db = migrated_database
    settings = _runtime(_settings(str(db.engine.url), tmp_path))
    with TestClient(create_app(settings=settings, database=db)) as client:
        owner = _register(client, "device-owner")
        agent = _create_owned_agent(client, human_id=owner["user"]["id"], handle="device-owner")
        auth = {"Authorization": f"Bearer {agent['api_key']}"}
        task = client.post(
            "/api/v1/agent/tasks",
            headers={**auth, "Idempotency-Key": "devices"},
            json={"title": "devices", "goal": "merge views", "expected_output": "proof"},
        ).json()
        task_id = UUID(task["task_id"])
        with db.session_factory() as session:
            first = _add_activity(
                session, task_id=task_id, kind="task_message", actor_type="platform"
            )
            second = _add_activity(
                session, task_id=task_id, kind="task_message", actor_type="platform"
            )
            session.flush()
            ids = [first.id, second.id]
            session.commit()
        barrier = Barrier(2)

        def view(activity_id):
            with db.session_factory() as session:
                human = session.get(HumanUser, UUID(owner["user"]["id"]))
                barrier.wait(timeout=5)
                return update_preference(
                    session,
                    user=human,
                    task_id=task_id,
                    payload=TaskPreferenceUpdate(seen_activity_ids=[activity_id]),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(view, ids))
        assert len(results) == 2
        with db.session_factory() as session:
            assert (
                preference_summary(session, task_id, UUID(owner["user"]["id"]))["unread_count"] == 0
            )
        pending = client.get(
            "/api/v1/task-runs/pending", headers=auth, params={"task_id": str(task_id)}
        ).json()["items"][0]
        barrier = Barrier(2)

        def claim(_):
            barrier.wait(timeout=5)
            return client.post(
                "/api/v1/task-runs/claim",
                headers=auth,
                json={"task_id": str(task_id), "assignment_id": pending["assignment_id"]},
            ).json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(claim, range(2)))
        assert sum(item is not None for item in claims) == 1
        assert next(item for item in claims if item)["run_id"] == pending["run_id"]
