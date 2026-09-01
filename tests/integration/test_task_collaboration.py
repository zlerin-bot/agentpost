from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from agentpost.config import Settings
from agentpost.db import Database
from agentpost.identity.models import utc_now
from agentpost.main import create_app
from agentpost.tasks.models import AgentRun

PASSWORD = "correct horse battery staple"
ADMIN_KEY = "admin-secret-admin-secret-admin-secret"
REGISTRATION_TOKEN = "task-agent-registration"


def _runtime(settings: Settings) -> Settings:
    return Settings(
        environment="test",
        database_url=settings.database_url,
        storage_path=settings.storage_path,
        api_key_pepper="test-agent-pepper",
        human_api_key_pepper="test-human-key-pepper",
        human_auth_secret="test-human-auth-secret",
        human_mfa_encryption_key="test-human-mfa-key",
        cursor_secret="test-cursor-secret",
        pairing_secret="test-pairing-secret",
        human_self_service_enabled=True,
        open_registration_enabled=True,
        registration_token=REGISTRATION_TOKEN,
        admin_token=ADMIN_KEY,
        email_delivery_mode="test",
        email_challenge_cooldown_seconds=10,
        public_base_url="https://agentpost.example",
        log_level="WARNING",
    )


def _register(client: TestClient, username: str) -> dict[str, object]:
    email = f"{username}@example.com"
    challenge = client.post(
        "/api/v1/auth/email/challenges", json={"email": email, "purpose": "register"}
    )
    body = challenge.json()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "challenge_id": body["challenge_id"],
            "code": body["test_verification_code"],
            "display_name": username,
            "username": username,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"{username}@example.com", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["csrf_token"])


def _create_owned_agent(client: TestClient, *, human_id: str, handle: str) -> dict[str, object]:
    created = client.post(
        "/api/v1/agents",
        headers={"X-Registration-Token": REGISTRATION_TOKEN},
        json={
            "address": f"{handle}@agents.local",
            "display_name": f"{handle}-ai",
            "capabilities": ["research", "document-delivery"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assigned = client.put(
        f"/api/v1/admin/humans/{human_id}/agents/{body['agent']['id']}",
        headers={"Authorization": f"Bearer {ADMIN_KEY}"},
        json={"role": "owner"},
    )
    assert assigned.status_code == 200, assigned.text
    return body


def test_confirmed_friends_task_agent_selection_run_and_human_acceptance(
    settings: Settings, database: Database
) -> None:
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        owner = _register(client, "task-owner")
        member = _register(client, "task-member")
        owner_agent = _create_owned_agent(
            client, human_id=str(owner["user"]["id"]), handle="task-owner"
        )
        member_agent = _create_owned_agent(
            client, human_id=str(member["user"]["id"]), handle="task-member"
        )

        owner_csrf = _login(client, "task-owner")
        requested = client.post(
            "/api/v1/friend-requests",
            headers={"X-CSRF-Token": owner_csrf},
            json={"username": "task-member"},
        )
        assert requested.status_code == 201, requested.text
        friendship_id = requested.json()["friendship_id"]
        assert requested.json()["relation_status"] == "pending_outgoing"

        member_csrf = _login(client, "task-member")
        incoming = client.get("/api/v1/friends")
        assert incoming.json()["items"][0]["relation_status"] == "pending_incoming"
        accepted = client.post(
            f"/api/v1/friend-requests/{friendship_id}/decision",
            headers={"X-CSRF-Token": member_csrf},
            json={"decision": "accept"},
        )
        assert accepted.status_code == 200, accepted.text

        owner_csrf = _login(client, "task-owner")
        owner_agent_id = owner_agent["agent"]["id"]
        created = client.post(
            "/api/v1/tasks",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "title": "联合完成客户方案",
                "goal": "形成双方确认的客户方案",
                "expected_output": "一份可验收的方案",
                "agent_ids": [owner_agent_id],
                "primary_agent_id": owner_agent_id,
            },
        )
        assert created.status_code == 201, created.text
        task = created.json()
        task_id = task["task_id"]
        assert task["members"][0]["agents"][0]["role"] == "primary"
        assert task["thread_id"]
        listed = client.get("/api/v1/tasks")
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["task_id"] == task_id

        invited = client.post(
            f"/api/v1/tasks/{task_id}/members",
            headers={"X-CSRF-Token": owner_csrf},
            json={"human_user_ids": [member["user"]["id"]]},
        )
        assert invited.status_code == 200, invited.text
        assert invited.json()["invited_member_count"] == 1

        member_csrf = _login(client, "task-member")
        missing_selection = client.post(
            f"/api/v1/tasks/{task_id}/accept",
            headers={"X-CSRF-Token": member_csrf},
            json={},
        )
        assert missing_selection.status_code == 422
        member_agent_id = member_agent["agent"]["id"]
        joined = client.post(
            f"/api/v1/tasks/{task_id}/accept",
            headers={"X-CSRF-Token": member_csrf},
            json={"agent_ids": [member_agent_id], "primary_agent_id": member_agent_id},
        )
        assert joined.status_code == 200, joined.text
        assert joined.json()["active_member_count"] == 2

        owner_csrf = _login(client, "task-owner")
        assigned = client.post(
            f"/api/v1/tasks/{task_id}/assignments",
            headers={"X-CSRF-Token": owner_csrf},
            json={
                "responsible_human_user_id": member["user"]["id"],
                "assignee_agent_id": member_agent_id,
                "instruction": "完成风险分析",
                "expected_output": "风险清单",
            },
        )
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["assignments"][0]["status"] == "queued"

        claim = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        assert claim.status_code == 200, claim.text
        run = claim.json()
        assert run["task_id"] == task_id
        assert run["security_label"] == "external_agent_content"

        heartbeat = client.post(
            f"/api/v1/task-runs/{run['run_id']}/heartbeat",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
            json={"lease_token": run["lease_token"], "status": "running"},
        )
        assert heartbeat.status_code == 200, heartbeat.text

        with database.session_factory() as session:
            leased_run = session.scalar(select(AgentRun).where(AgentRun.id == UUID(run["run_id"])))
            assert leased_run is not None
            leased_run.lease_expires_at = utc_now() - timedelta(seconds=1)
            session.commit()

        reclaimed = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        assert reclaimed.status_code == 200, reclaimed.text
        reclaimed_run = reclaimed.json()
        assert reclaimed_run["run_id"] != run["run_id"]
        assert reclaimed_run["attempt"] == 2

        result = client.post(
            f"/api/v1/task-runs/{reclaimed_run['run_id']}/result",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
            json={
                "lease_token": reclaimed_run["lease_token"],
                "status": "completed",
                "summary": "识别三项风险并给出措施",
            },
        )
        assert result.status_code == 204, result.text

        owner_csrf = _login(client, "task-owner")
        detail = client.get(f"/api/v1/tasks/{task_id}")
        assert detail.json()["assignments"][0]["result_status"] == "completed"
        submitted = client.post(
            f"/api/v1/tasks/{task_id}/submit",
            headers={"X-CSRF-Token": owner_csrf},
            json={"summary": "最终客户方案已经形成"},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "awaiting_acceptance"
        completed = client.post(
            f"/api/v1/tasks/{task_id}/acceptance",
            headers={"X-CSRF-Token": owner_csrf},
            json={"decision": "accept"},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "completed"


def test_message_history_is_only_a_friend_suggestion(
    settings: Settings, database: Database
) -> None:
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        owner = _register(client, "suggest-owner")
        candidate = _register(client, "suggest-candidate")
        owner_agent = _create_owned_agent(
            client, human_id=str(owner["user"]["id"]), handle="suggest-owner"
        )
        candidate_agent = _create_owned_agent(
            client, human_id=str(candidate["user"]["id"]), handle="suggest-candidate"
        )
        sent = client.post(
            "/api/v1/messages",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "friend-suggestion-contact",
            },
            json={
                "to": [{"address": candidate_agent["agent"]["address"]}],
                "type": "message",
                "subject": "认识一下",
                "content": {"format": "text", "body": "hello"},
            },
        )
        assert sent.status_code == 201, sent.text
        _login(client, "suggest-owner")
        friends = client.get("/api/v1/friends")
        assert friends.json()["items"] == []
        suggestions = client.get("/api/v1/friends/suggestions")
        assert suggestions.json()["items"][0]["relation_status"] == "suggested"
