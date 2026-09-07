from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_task_collaboration import _create_owned_agent, _login, _register, _runtime

from agentpost.main import create_app
from agentpost.tasks.models import AgentRun, TaskAgentParticipant, TaskAssignment


def test_personal_preferences_snapshot_and_exit(settings, database):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        owner = _register(client, "prefs-owner")
        agent = _create_owned_agent(client, human_id=owner["user"]["id"], handle="prefs-owner")
        member = _register(client, "prefs-member")
        member_agent = _create_owned_agent(
            client, human_id=member["user"]["id"], handle="prefs-member"
        )
        auth = {"Authorization": f"Bearer {agent['api_key']}"}
        task = client.post(
            "/api/v1/agent/tasks",
            headers={**auth, "Idempotency-Key": "prefs"},
            json={"title": "prefs", "goal": "test", "expected_output": "proof"},
        ).json()
        url = f"/api/v1/tasks/{task['task_id']}"
        csrf = _login(client, "prefs-owner")
        headers = {"X-CSRF-Token": csrf}
        assert client.post(url + "/leave", headers=headers).status_code == 409
        assert (
            client.patch(url + "/preferences", json={"list_state": "archived"}).status_code == 403
        )
        friend = client.post(
            "/api/v1/friend-requests", headers=headers, json={"username": "prefs-member"}
        ).json()
        other = {"X-CSRF-Token": _login(client, "prefs-member")}
        assert (
            client.patch(
                url + "/preferences", headers=other, json={"list_state": "archived"}
            ).status_code
            == 404
        )
        client.post(
            f"/api/v1/friend-requests/{friend['friendship_id']}/decision",
            headers=other,
            json={"decision": "accept"},
        )
        headers = {"X-CSRF-Token": _login(client, "prefs-owner")}
        assert (
            client.post(
                url + "/members", headers=headers, json={"human_user_ids": [member["user"]["id"]]}
            ).status_code
            == 200
        )
        message_url = f"/api/v1/agent/tasks/{task['task_id']}/messages"
        first = client.post(
            message_url, headers={**auth, "Idempotency-Key": "m1"}, json={"body": "one"}
        ).json()
        other = {"X-CSRF-Token": _login(client, "prefs-member")}
        before = client.get(url).json()
        assert before["unread_count"] == 1
        assert client.get(url).json()["unread_count"] == 1  # GET never marks Human or Agent read.
        client.post(message_url, headers={**auth, "Idempotency-Key": "m2"}, json={"body": "two"})
        pref = client.patch(
            url + "/preferences",
            headers=other,
            json={
                "seen_activity_ids": [first["activity_id"]],
                "list_state": "archived",
            },
        )
        assert pref.status_code == 200, pref.text
        assert pref.json()["unread_count"] == 1  # Late message survives snapshot, after archiving.
        assert client.get(url).json()["status"] == before["status"]
        assert (
            client.patch(
                url + "/preferences", headers=other, json={"list_state": "deleted"}
            ).json()["personal_state"]
            == "deleted"
        )
        assert (
            client.patch(url + "/preferences", headers=other, json={"list_state": "active"}).json()[
                "personal_state"
            ]
            == "active"
        )
        headers = {"X-CSRF-Token": _login(client, "prefs-owner")}
        assert client.get(url).json()["personal_state"] == "active"
        other = {"X-CSRF-Token": _login(client, "prefs-member")}
        assert client.post(url + "/leave", headers=other).status_code == 204
        assert client.get(url).status_code == 404
        assert (
            client.get(
                f"/api/v1/agent/tasks/{task['task_id']}",
                headers={"Authorization": f"Bearer {member_agent['api_key']}"},
            ).status_code
            == 404
        )
        _login(client, "prefs-owner")
        remaining = client.get(url)
        assert remaining.status_code == 200, remaining.text
        assert len(remaining.json()["members"]) == 1
        assert any(
            a["responsible_human_display_name"] == "prefs-member"
            for a in remaining.json()["assignments"]
        )
        with database.session_factory() as session:
            participants = session.scalars(
                select(TaskAgentParticipant).where(
                    TaskAgentParticipant.human_user_id == UUID(member["user"]["id"])
                )
            ).all()
            assert participants and all(not p.active for p in participants)
            assignments = session.scalars(
                select(TaskAssignment).where(
                    TaskAssignment.responsible_human_user_id == UUID(member["user"]["id"])
                )
            ).all()
            assert assignments and all(a.status == "cancelled" for a in assignments)
            runs = session.scalars(
                select(AgentRun).where(AgentRun.assignment_id.in_([a.id for a in assignments]))
            ).all()
            assert all(r.status == "cancelled" and r.lease_token_digest is None for r in runs)

        headers = {"X-CSRF-Token": _login(client, "prefs-owner")}
        reinvited = client.post(
            url + "/members", headers=headers, json={"human_user_ids": [member["user"]["id"]]}
        )
        assert reinvited.status_code == 200, reinvited.text
        _login(client, "prefs-member")
        assert client.get(url).status_code == 200
