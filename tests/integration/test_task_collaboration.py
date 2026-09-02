from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from agentpost.config import Settings
from agentpost.db import Database
from agentpost.identity.models import utc_now
from agentpost.main import create_app
from agentpost.onboarding.models import AgentConnectorBinding, ConnectorInstance
from agentpost.tasks.models import AgentRun, TaskActivity, TaskAssignment

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

        owner_agent_id = owner_agent["agent"]["id"]
        created = client.post(
            "/api/v1/agent/tasks",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "two-human-task-create",
            },
            json={
                "title": "联合完成客户方案",
                "goal": "形成双方确认的客户方案",
                "expected_output": "一份可验收的方案",
            },
        )
        assert created.status_code == 201, created.text
        task = created.json()
        task_id = task["task_id"]
        assert task["members"][0]["agents"][0]["role"] == "primary"
        assert task["members"][0]["primary_agent_id"] == owner_agent_id
        assert task["thread_id"]
        assert task["task_id"]
        repeated = client.post(
            "/api/v1/agent/tasks",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "two-human-task-create",
            },
            json={
                "title": "联合完成客户方案",
                "goal": "形成双方确认的客户方案",
                "expected_output": "一份可验收的方案",
            },
        )
        assert repeated.status_code == 201, repeated.text
        assert repeated.json()["task_id"] == task_id
        owner_csrf = _login(client, "task-owner")
        listed = client.get("/api/v1/tasks")
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["task_id"] == task_id

        invited = client.post(
            f"/api/v1/tasks/{task_id}/members",
            headers={"X-CSRF-Token": owner_csrf},
            json={"human_user_ids": [member["user"]["id"]]},
        )
        assert invited.status_code == 200, invited.text
        invited_body = invited.json()
        assert invited_body["active_member_count"] == 2
        assert invited_body["invited_member_count"] == 0
        added_member = next(
            item
            for item in invited_body["members"]
            if item["human_user_id"] == member["user"]["id"]
        )
        member_agent_id = member_agent["agent"]["id"]
        assert added_member["status"] == "active"
        assert added_member["primary_agent_id"] == member_agent_id
        assert added_member["agent_selection_source"] == "default"
        assert added_member["email_notification_status"] == "sent"

        member_csrf = _login(client, "task-member")
        member_tasks = client.get("/api/v1/tasks")
        assert member_tasks.status_code == 200, member_tasks.text
        assert member_tasks.json()["items"][0]["task_id"] == task_id
        selected = client.put(
            f"/api/v1/tasks/{task_id}/my-agents",
            headers={"X-CSRF-Token": member_csrf},
            json={"agent_ids": [member_agent_id], "primary_agent_id": member_agent_id},
        )
        assert selected.status_code == 200, selected.text
        selected_member = next(
            item
            for item in selected.json()["members"]
            if item["human_user_id"] == member["user"]["id"]
        )
        assert selected_member["agent_selection_source"] == "selected"
        assert len(selected.json()["assignments"]) == 2

        owner_run_response = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {owner_agent['api_key']}"},
        )
        assert owner_run_response.status_code == 200, owner_run_response.text
        owner_run = owner_run_response.json()
        assert owner_run["task_id"] == task_id
        assert set(owner_run["participant_agent_ids"]) == {owner_agent_id, member_agent_id}
        owner_result = client.post(
            f"/api/v1/task-runs/{owner_run['run_id']}/result",
            headers={"Authorization": f"Bearer {owner_agent['api_key']}"},
            json={
                "lease_token": owner_run["lease_token"],
                "status": "completed",
                "summary": "已整理目标、材料与协同边界",
                "output": {"legacy_connector": True},
            },
        )
        assert owner_result.status_code == 204, owner_result.text

        claim = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        assert claim.status_code == 200, claim.text
        run = claim.json()
        assert run["task_id"] == task_id
        assert run["security_label"] == "external_agent_content"
        assert run["collaboration_updates"][0]["summary"] == "已整理目标、材料与协同边界"

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

        owner_sync_response = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {owner_agent['api_key']}"},
        )
        assert owner_sync_response.status_code == 200, owner_sync_response.text
        owner_sync = owner_sync_response.json()
        assert "识别三项风险并给出措施" in owner_sync["instruction"]
        assert len(owner_sync["collaboration_updates"]) == 2
        owner_sync_result = client.post(
            f"/api/v1/task-runs/{owner_sync['run_id']}/result",
            headers={"Authorization": f"Bearer {owner_agent['api_key']}"},
            json={
                "lease_token": owner_sync["lease_token"],
                "status": "completed",
                "summary": "已校验风险措施，可以汇总",
            },
        )
        assert owner_sync_result.status_code == 204, owner_sync_result.text

        member_sync_response = client.post(
            "/api/v1/task-runs/claim",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        assert member_sync_response.status_code == 200, member_sync_response.text
        member_sync = member_sync_response.json()
        assert "已整理目标、材料与协同边界" in member_sync["instruction"]
        member_sync_result = client.post(
            f"/api/v1/task-runs/{member_sync['run_id']}/result",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
            json={
                "lease_token": member_sync["lease_token"],
                "status": "completed",
                "summary": "已吸收共同目标，无需补充",
            },
        )
        assert member_sync_result.status_code == 204, member_sync_result.text

        owner_csrf = _login(client, "task-owner")
        detail = client.get(f"/api/v1/tasks/{task_id}")
        assert all(
            assignment["result_status"] == "completed"
            for assignment in detail.json()["assignments"]
        )
        assert detail.json()["state_axes"]["agent_result_status"] == "completed"
        assert detail.json()["state_axes"]["human_acceptance_status"] == "not_ready"
        submitted = client.post(
            f"/api/v1/tasks/{task_id}/submit",
            headers={"X-CSRF-Token": owner_csrf},
            json={"summary": "最终客户方案已经形成"},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "awaiting_acceptance"
        assert submitted.json()["state_axes"]["submission_status"] == "awaiting_acceptance"
        assert submitted.json()["state_axes"]["human_acceptance_status"] == "pending"
        missing_change_note = client.post(
            f"/api/v1/tasks/{task_id}/acceptance",
            headers={"X-CSRF-Token": owner_csrf},
            json={"decision": "request_changes"},
        )
        assert missing_change_note.status_code == 422, missing_change_note.text
        changes = client.post(
            f"/api/v1/tasks/{task_id}/acceptance",
            headers={"X-CSRF-Token": owner_csrf},
            json={"decision": "request_changes", "note": "补充风险处置时限"},
        )
        assert changes.status_code == 200, changes.text
        assert changes.json()["revision"] == 2
        assert changes.json()["state_axes"]["submission_status"] == "changes_requested"
        assert changes.json()["state_axes"]["human_acceptance_status"] == "changes_requested"
        assert changes.json()["state_axes"]["run_counts"]["queued"] == 2
        assert changes.json()["state_axes"]["agent_result_status"] == "mixed"

        for agent in (owner_agent, member_agent):
            revision_run = client.post(
                "/api/v1/task-runs/claim",
                headers={"Authorization": f"Bearer {agent['api_key']}"},
            )
            assert revision_run.status_code == 200, revision_run.text
            revision_run_body = revision_run.json()
            assert "补充风险处置时限" in revision_run_body["instruction"]
            revision_result = client.post(
                f"/api/v1/task-runs/{revision_run_body['run_id']}/result",
                headers={"Authorization": f"Bearer {agent['api_key']}"},
                json={
                    "lease_token": revision_run_body["lease_token"],
                    "status": "completed",
                    "summary": "已按修改意见补充",
                },
            )
            assert revision_result.status_code == 204, revision_result.text

        resubmitted = client.post(
            f"/api/v1/tasks/{task_id}/submit",
            headers={"X-CSRF-Token": owner_csrf},
            json={"summary": "最终客户方案已补充风险处置时限"},
        )
        assert resubmitted.status_code == 200, resubmitted.text
        completed = client.post(
            f"/api/v1/tasks/{task_id}/acceptance",
            headers={"X-CSRF-Token": owner_csrf},
            json={"decision": "accept"},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "completed"
        assert completed.json()["state_axes"]["human_acceptance_status"] == "accepted"


def test_task_messages_use_legacy_inbox_and_native_run_without_breaking_old_connectors(
    settings: Settings, database: Database
) -> None:
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        owner = _register(client, "message-owner")
        member = _register(client, "message-member")
        outsider = _register(client, "message-outsider")
        owner_agent = _create_owned_agent(
            client, human_id=str(owner["user"]["id"]), handle="message-owner"
        )
        member_agent = _create_owned_agent(
            client, human_id=str(member["user"]["id"]), handle="message-member"
        )
        outsider_agent = _create_owned_agent(
            client, human_id=str(outsider["user"]["id"]), handle="message-outsider"
        )

        owner_csrf = _login(client, "message-owner")
        friendship = client.post(
            "/api/v1/friend-requests",
            headers={"X-CSRF-Token": owner_csrf},
            json={"username": "message-member"},
        ).json()
        member_csrf = _login(client, "message-member")
        accepted = client.post(
            f"/api/v1/friend-requests/{friendship['friendship_id']}/decision",
            headers={"X-CSRF-Token": member_csrf},
            json={"decision": "accept"},
        )
        assert accepted.status_code == 200, accepted.text

        created = client.post(
            "/api/v1/agent/tasks",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "message-task-create",
            },
            json={
                "title": "测试任务",
                "goal": "验证新旧连接兼容",
                "expected_output": "任务消息进入同一任务",
            },
        )
        assert created.status_code == 201, created.text
        task = created.json()
        task_id = task["task_id"]
        owner_csrf = _login(client, "message-owner")
        invited = client.post(
            f"/api/v1/tasks/{task_id}/members",
            headers={"X-CSRF-Token": owner_csrf},
            json={"human_user_ids": [member["user"]["id"]]},
        )
        assert invited.status_code == 200, invited.text

        context = client.get(
            f"/api/v1/agent/tasks/{task_id}",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        assert context.status_code == 200, context.text
        assert context.json()["title"] == "测试任务"
        hidden = client.get(
            f"/api/v1/agent/tasks/{task_id}",
            headers={"Authorization": f"Bearer {outsider_agent['api_key']}"},
        )
        assert hidden.status_code == 404

        legacy = client.post(
            f"/api/v1/agent/tasks/{task_id}/messages",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "legacy-task-message",
            },
            json={"subject": "兼容测试", "format": "text", "body": "请确认收到"},
        )
        assert legacy.status_code == 201, legacy.text
        assert legacy.json()["legacy_delivery_count"] == 1
        assert legacy.json()["queued_run_count"] == 0
        replay = client.post(
            f"/api/v1/agent/tasks/{task_id}/messages",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "legacy-task-message",
            },
            json={"subject": "兼容测试", "content_format": "text", "body": "请确认收到"},
        )
        assert replay.status_code == 201, replay.text
        assert replay.json()["replayed"] is True
        conflict = client.post(
            f"/api/v1/agent/tasks/{task_id}/messages",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "legacy-task-message",
            },
            json={"subject": "兼容测试", "content_format": "text", "body": "不同正文"},
        )
        assert conflict.status_code == 409

        inbox = client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {member_agent['api_key']}"},
        )
        bridge = next(
            item for item in inbox.json()["items"] if item["metadata"].get("agentpost_task_bridge")
        )
        assert bridge["thread_id"] == task["thread_id"]
        assert bridge["metadata"]["agentpost_task_id"] == task_id
        reply = client.post(
            f"/api/v1/messages/{bridge['message_id']}/reply",
            headers={
                "Authorization": f"Bearer {member_agent['api_key']}",
                "Idempotency-Key": "legacy-task-reply",
            },
            json={
                "type": "message",
                "subject": "已收到",
                "content": {"format": "text", "body": "旧连接已收到并回复"},
            },
        )
        assert reply.status_code == 201, reply.text

        member_agent_id = UUID(member_agent["agent"]["id"])
        with database.session_factory() as session:
            session.add(
                ConnectorInstance(
                    connector_id="message-member-current",
                    agent_id=member_agent_id,
                    human_user_id=UUID(member["user"]["id"]),
                    connector_type="codex",
                    display_name="message-member-current",
                    client_version="agentpost-connect/0.1.20",
                    runtime_version="agentpost-connect/0.1.40",
                    status="active",
                    health_status="healthy",
                )
            )
            session.flush()
            connector = session.scalar(
                select(ConnectorInstance).where(
                    ConnectorInstance.connector_id == "message-member-current"
                )
            )
            assert connector is not None
            session.add(
                AgentConnectorBinding(
                    agent_id=member_agent_id,
                    connector_instance_id=connector.id,
                )
            )
            session.commit()

        native = client.post(
            f"/api/v1/agent/tasks/{task_id}/messages",
            headers={
                "Authorization": f"Bearer {owner_agent['api_key']}",
                "Idempotency-Key": "native-task-message",
            },
            json={"content_format": "markdown", "body": "请继续协同"},
        )
        assert native.status_code == 201, native.text
        assert native.json()["queued_run_count"] == 1
        assert native.json()["legacy_delivery_count"] == 0

        owner_csrf = _login(client, "message-owner")
        task_detail = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"X-CSRF-Token": owner_csrf},
        )
        assert task_detail.status_code == 200, task_detail.text
        native_activity = next(
            item
            for item in task_detail.json()["activities"]
            if item["metadata"].get("body") == "请继续协同"
        )
        assert native_activity["actor_display_name"] == "message-owner"
        assert native_activity["actor_agent_display_name"] == "message-owner-ai"
        assert native_activity["metadata"]["content_format"] == "markdown"

        with database.session_factory() as session:
            message_activities = list(
                session.scalars(
                    select(TaskActivity).where(
                        TaskActivity.task_id == UUID(task_id),
                        TaskActivity.activity_type == "task_message",
                    )
                )
            )
            assert {item.activity_metadata.get("body") for item in message_activities} == {
                "请确认收到",
                "旧连接已收到并回复",
                "请继续协同",
            }
            native_assignments = list(
                session.scalars(
                    select(TaskAssignment).where(
                        TaskAssignment.task_id == UUID(task_id),
                        TaskAssignment.assignment_kind == "task_message",
                    )
                )
            )
            assert len(native_assignments) == 1
            assert native_assignments[0].assignee_agent_id == member_agent_id


def test_agent_resolves_only_its_participating_tasks_by_exact_title(
    settings: Settings, database: Database
) -> None:
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        owner = _register(client, "resolve-owner")
        other = _register(client, "resolve-other")
        participating_agent = _create_owned_agent(
            client, human_id=str(owner["user"]["id"]), handle="resolve-participant"
        )
        same_human_unselected_agent = _create_owned_agent(
            client, human_id=str(owner["user"]["id"]), handle="resolve-unselected"
        )
        unrelated_agent = _create_owned_agent(
            client, human_id=str(other["user"]["id"]), handle="resolve-unrelated"
        )

        def create(title: str, key: str) -> dict[str, object]:
            response = client.post(
                "/api/v1/agent/tasks",
                headers={
                    "Authorization": f"Bearer {participating_agent['api_key']}",
                    "Idempotency-Key": key,
                },
                json={
                    "title": title,
                    "goal": "验证任务名称解析",
                    "expected_output": "返回稳定任务 ID",
                },
            )
            assert response.status_code == 201, response.text
            return response.json()

        unique_task = create("ＨｉＰｉ 知识库", "resolve-unique")
        duplicate_tasks = [create("小孔成像", f"resolve-duplicate-{index}") for index in range(6)]

        exact = client.post(
            "/api/v1/agent/tasks/resolve",
            headers={"Authorization": f"Bearer {participating_agent['api_key']}"},
            json={"query": "hipi   知识库"},
        )
        assert exact.status_code == 200, exact.text
        exact_body = exact.json()
        assert exact_body["status"] == "resolved"
        assert exact_body["reason"] == "unique_exact_title"
        assert exact_body["match"]["task_id"] == unique_task["task_id"]
        assert exact_body["match"]["match_kind"] == "exact"
        assert exact_body["match"]["security_label"] == "external_agent_content"

        duplicate = client.post(
            "/api/v1/agent/tasks/resolve",
            headers={"Authorization": f"Bearer {participating_agent['api_key']}"},
            json={"query": "小孔成像"},
        )
        assert duplicate.status_code == 200, duplicate.text
        duplicate_body = duplicate.json()
        assert duplicate_body["status"] == "needs_clarification"
        assert duplicate_body["reason"] == "duplicate_exact_title"
        assert duplicate_body["total_candidates"] == len(duplicate_tasks)
        assert len(duplicate_body["candidates"]) == 5

        partial = client.post(
            "/api/v1/agent/tasks/resolve",
            headers={"Authorization": f"Bearer {participating_agent['api_key']}"},
            json={"query": "请给 hipi 知识库任务发消息"},
        )
        assert partial.status_code == 200, partial.text
        assert partial.json()["status"] == "needs_clarification"
        assert partial.json()["reason"] == "partial_title_requires_confirmation"

        for hidden_agent in (same_human_unselected_agent, unrelated_agent):
            hidden = client.post(
                "/api/v1/agent/tasks/resolve",
                headers={"Authorization": f"Bearer {hidden_agent['api_key']}"},
                json={"query": "小孔成像"},
            )
            assert hidden.status_code == 200, hidden.text
            assert hidden.json()["status"] == "not_found"
            assert hidden.json()["candidates"] == []

        blank = client.post(
            "/api/v1/agent/tasks/resolve",
            headers={"Authorization": f"Bearer {participating_agent['api_key']}"},
            json={"query": "   "},
        )
        assert blank.status_code == 422, blank.text


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
