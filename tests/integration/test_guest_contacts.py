import secrets
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_task_collaboration import _create_owned_agent, _login, _register, _runtime

from agentpost.contacts.models import ContactRequest
from agentpost.identity.models import utc_now
from agentpost.main import create_app
from agentpost.tasks.models import AgentRun, Task, TaskActivity, TaskMembership


def setup_receiver(client, username="receiver", *, save_preference=True):
    person = _register(client, username)
    agent = _create_owned_agent(client, human_id=person["user"]["id"], handle=username)
    csrf = _login(client, username)
    headers = {"X-CSRF-Token": csrf}
    result = client.put(f"/api/v1/orbit/agents/{agent['agent']['id']}/default", headers=headers)
    assert result.status_code == 200, result.text
    if save_preference:
        result = client.put("/api/v1/contacts/preferences", headers=headers, json={"enabled": True})
        assert result.status_code == 200, result.text
    return person, agent, headers


def send(client, name="receiver", token=None, intent="collaboration"):
    token = token or "gc_" + secrets.token_urlsafe(32)
    payload = {
        "username": name,
        "intent": intent,
        "sender_name": "Guest",
        "subject": "首次咨询",
        "body": "<script>alert(1)</script>\n具体情况",
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/public/contact/requests", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json(), token, headers, payload


def test_guest_contact_full_claim_accept_and_task_boundary(settings, database):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        receiver, agent, headers = setup_receiver(client)
        assert client.get("/api/v1/public/contact/resolve?username=receiver").json() == {
            "username": "receiver",
            "display_name": "receiver",
            "introduction": "",
            "contact_url": f"{_runtime(settings).public_base_url.rstrip('/')}/contact?to=receiver",
            "match": "exact",
            "status": "resolved",
            "accepts_first_contact": True,
        }
        item, token, guest, payload = send(client)
        contact_id = item["request_id"]
        assert item["status"] == "waiting_recipient"
        assert client.get(f"/api/v1/public/contact/requests/{contact_id}").status_code == 401
        assert (
            client.get(f"/api/v1/public/contact/requests/{uuid4()}", headers=guest).status_code
            == 404
        )
        replay = client.post("/api/v1/public/contact/requests", headers=guest, json=payload)
        assert replay.json()["request_id"] == contact_id
        assert (
            client.post(
                "/api/v1/public/contact/requests",
                headers=guest,
                json={**payload, "body": "changed"},
            ).status_code
            == 409
        )
        inbox = client.get(
            "/api/v1/agent/contact-requests",
            headers={"Authorization": f"Bearer {agent['api_key']}"},
        )
        assert inbox.status_code == 200, inbox.text
        assert inbox.json()["items"][0]["body"] == payload["body"]
        assert token not in inbox.text
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
            assert session.scalar(select(func.count()).select_from(Task)) == 0
        accepted = client.post(
            f"/api/v1/contacts/{contact_id}/decision", headers=headers, json={"action": "accept"}
        )
        assert accepted.json()["status"] == "waiting_registration", accepted.text
        sender = _register(client, "sender")
        sender_headers = {"X-CSRF-Token": _login(client, "sender")}
        assert client.post("/api/v1/contacts/claim", json={"token": token}).status_code == 403
        claimed = client.post(
            "/api/v1/contacts/claim", headers=sender_headers, json={"token": token}
        )
        assert claimed.json()["status"] == "waiting_agents", claimed.text
        assert (
            client.get(f"/api/v1/public/contact/requests/{contact_id}", headers=guest).json()[
                "status"
            ]
            == "claimed"
        )
        sender_agent = _create_owned_agent(client, human_id=sender["user"]["id"], handle="sender")
        client.put(
            f"/api/v1/orbit/agents/{sender_agent['agent']['id']}/default", headers=sender_headers
        ).raise_for_status()
        result = client.post(
            f"/api/v1/contacts/{contact_id}/decision",
            headers=sender_headers,
            json={"action": "continue"},
        )
        assert result.status_code == 200, result.text
        task_id = result.json()["task_id"]
        assert task_id
        repeat = client.post(
            f"/api/v1/contacts/{contact_id}/decision",
            headers=sender_headers,
            json={"action": "continue"},
        )
        assert repeat.json()["task_id"] == task_id
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Task)) == 1
            assert session.scalar(select(func.count()).select_from(TaskMembership)) == 2
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 2
            original = session.scalar(
                select(TaskActivity).where(TaskActivity.activity_type == "task_message")
            )
            assert original.activity_metadata["body"] == payload["body"]
            assert original.security_label == "external_agent_content"
        assert (
            client.get(
                f"/api/v1/agent/tasks/{task_id}",
                headers={"Authorization": f"Bearer {sender_agent['api_key']}"},
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/agent/tasks/{task_id}", headers=guest).status_code == 401


def test_private_recipient_decline_and_claim_ownership(settings, database):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, _, headers = setup_receiver(client)
        item, token, guest, _ = send(client)
        cid = item["request_id"]
        assert (
            client.post(
                "/api/v1/contacts/claim", headers=headers, json={"token": token}
            ).status_code
            == 404
        )
        client.put(
            "/api/v1/contacts/preferences", headers=headers, json={"enabled": False}
        ).raise_for_status()
        assert client.get("/api/v1/public/contact/resolve?username=receiver").status_code == 404
        assert client.get("/api/v1/public/contact/resolve?username=unknown").status_code == 404
        rejected = client.post(
            f"/api/v1/contacts/{cid}/decision", headers=headers, json={"action": "decline"}
        )
        assert rejected.json()["status"] == "declined"
        _register(client, "outsider")
        outsider = {"X-CSRF-Token": _login(client, "outsider")}
        assert client.get("/api/v1/contacts").json()["items"] == []
        assert (
            client.post(
                f"/api/v1/contacts/{cid}/decision", headers=outsider, json={"action": "accept"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/contacts/claim", headers=outsider, json={"token": token}
            ).status_code
            == 200
        )
        _register(client, "thief")
        thief = {"X-CSRF-Token": _login(client, "thief")}
        assert (
            client.post("/api/v1/contacts/claim", headers=thief, json={"token": token}).status_code
            == 404
        )
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Task)) == 0
            row = session.get(ContactRequest, UUID(cid))
            row.expires_at = utc_now() - timedelta(seconds=1)
            session.commit()
        assert (
            client.get(f"/api/v1/public/contact/requests/{cid}", headers=guest).json()["status"]
            == "claimed"
        )


def test_expired_and_rate_limited_requests(settings, database):
    runtime = _runtime(settings).model_copy(update={"rate_limit_enabled": True})
    with TestClient(create_app(settings=runtime, database=database)) as client:
        _, _, headers = setup_receiver(client)
        item, token, guest, payload = send(client)
        with database.session_factory() as session:
            row = session.get(ContactRequest, UUID(item["request_id"]))
            row.expires_at = utc_now() - timedelta(seconds=1)
            session.commit()
        assert (
            client.get(
                f"/api/v1/public/contact/requests/{item['request_id']}", headers=guest
            ).json()["status"]
            == "expired"
        )
        assert (
            client.post(
                f"/api/v1/contacts/{item['request_id']}/decision",
                headers=headers,
                json={"action": "accept"},
            ).status_code
            == 409
        )
        for _ in range(4):
            send(client)
        blocked = client.post(
            "/api/v1/public/contact/requests",
            headers={"Authorization": "Bearer gc_" + secrets.token_urlsafe(32)},
            json=payload,
        )
        assert blocked.status_code == 429, blocked.text
        assert blocked.headers.get("Retry-After")


def test_browser_guest_resume_and_default_agent_routing(settings, database):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, old_agent, headers = setup_receiver(client)
        item, token, _, _ = send(client)
        assert (
            client.post("/api/v1/contacts/guest-session", json={"token": token}).status_code == 403
        )
        saved = client.post(
            "/api/v1/contacts/guest-session",
            headers={"X-AgentPost-Guest": "1"},
            json={"token": token},
        )
        assert saved.status_code == 200
        cookie = saved.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert client.get("/api/v1/contacts/guest-session").json()["pending_claim"]
        assert token not in client.get("/api/v1/contacts/guest-session").text
        assert client.get("/api/v1/contacts/summary").json()["pending_count"] == 1
        _register(client, "browser-sender")
        csrf = _login(client, "browser-sender")
        claimed = client.post("/api/v1/contacts/claim", headers={"X-CSRF-Token": csrf}, json={})
        assert claimed.status_code == 200, claimed.text
        assert not client.get("/api/v1/contacts/guest-session").json()["pending_claim"]
        assert not client.get("/api/v1/contacts/summary").json()["pending_count"]
        assert (
            client.get(
                "/api/v1/agent/contact-requests",
                headers={"Authorization": f"Bearer {old_agent['api_key']}"},
            ).json()["items"][0]["request_id"]
            == item["request_id"]
        )


def test_concurrent_continuation_creates_one_task(settings, database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from agentpost.contacts.service import continue_contact, lock_contact

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        setup_receiver(client)
        item, _, _, _ = send(client)
        sender, _, _ = setup_receiver(client, "parallel-sender")
        cid = UUID(item["request_id"])
        with database.session_factory() as session:
            row = session.get(ContactRequest, cid)
            row.sender_id = UUID(sender["user"]["id"])
            row.decision = "accepted"
            session.commit()
        barrier = Barrier(2)

        def finalize():
            with database.session_factory() as session:
                barrier.wait()
                row = lock_contact(session, cid)
                continue_contact(session, row)
                session.commit()
                return row.task_id

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: finalize(), range(2)))
        assert results[0] == results[1]
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Task)) == 1
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 2


def test_agent_contact_pages_are_scoped_and_complete(settings, database):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        receiver, agent, _ = setup_receiver(client)
        with database.session_factory() as session:
            for _ in range(23):
                session.add(
                    ContactRequest(
                        token_digest=secrets.token_hex(32),
                        payload_digest="0" * 64,
                        recipient_id=UUID(receiver["user"]["id"]),
                        sender_name="guest",
                        subject="page",
                        body="text",
                        expires_at=utc_now() + timedelta(days=7),
                    )
                )
            session.commit()
        headers = {"Authorization": f"Bearer {agent['api_key']}"}
        first = client.get("/api/v1/agent/contact-requests", headers=headers).json()
        assert len(first["items"]) == 20 and first["next_cursor"]
        second = client.get(
            "/api/v1/agent/contact-requests",
            headers=headers,
            params={"before": first["next_cursor"]},
        ).json()
        assert len(second["items"]) == 3 and second["next_cursor"] is None
        assert len({x["request_id"] for x in first["items"] + second["items"]}) == 23
        assert (
            client.get(
                "/api/v1/agent/contact-requests", headers=headers, params={"before": str(uuid4())}
            ).status_code
            == 404
        )
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 0


def test_greeting_reply_claim_never_creates_task_or_friendship(settings, database):
    from agentpost.tasks.models import Friendship

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, _, headers = setup_receiver(client)
        item, token, guest, payload = send(client, intent="greeting")
        cid = item["request_id"]
        endpoint = f"/api/v1/contacts/{cid}/decision"
        assert client.post(endpoint, headers=headers, json={"action": "accept"}).status_code == 409
        reply = {"action": "reply", "body": "欢迎，先补充协作目标。"}
        assert client.post(endpoint, headers=headers, json=reply).status_code == 200
        assert client.post(endpoint, headers=headers, json=reply).status_code == 200
        assert (
            client.post(endpoint, headers=headers, json={**reply, "body": "第二条"}).status_code
            == 409
        )
        result = client.get(f"/api/v1/public/contact/requests/{cid}", headers=guest).json()
        assert result["reply"] == reply["body"] and result["status"] == "replied"
        assert "task_id" not in result
        sender, _, sender_headers = setup_receiver(client, "greeting-sender")
        claim = client.post("/api/v1/contacts/claim", headers=sender_headers, json={"token": token})
        assert claim.json()["next_action"] == "request_collaboration"
        assert (
            client.get(f"/api/v1/public/contact/requests/{cid}", headers=guest).json()["reply"]
            is None
        )
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Task)) == 0
            assert session.scalar(select(func.count()).select_from(Friendship)) == 0
        assert (
            client.post(
                endpoint, headers=sender_headers, json={"action": "request_collaboration"}
            ).status_code
            == 200
        )
        receiver_headers = {"X-CSRF-Token": _login(client, "receiver")}
        result = client.post(endpoint, headers=receiver_headers, json={"action": "accept"})
        assert result.json()["task_id"]
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Friendship)) == 1
            assert session.scalar(select(func.count()).select_from(Task)) == 1
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(TaskActivity)
                    .where(TaskActivity.activity_type == "task_message")
                )
                == 2
            )


def test_contact_report_blocks_followups_and_qr_matches_public_link(
    settings, database, monkeypatch
):
    import segno

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, _, headers = setup_receiver(client)
        client.put(
            "/api/v1/contacts/preferences",
            headers=headers,
            json={"enabled": True, "introduction": "欢迎交流"},
        ).raise_for_status()
        target = client.get("/api/v1/public/contact/resolve?username=receiver").json()
        assert target["introduction"] == "欢迎交流"
        encoded = []
        original = segno.make_qr

        def record(value):
            encoded.append(value)
            return original(value)

        monkeypatch.setattr(segno, "make_qr", record)
        qr = client.get("/api/v1/public/contact/qr?username=receiver")
        assert qr.status_code == 200 and "<svg" in qr.text
        assert encoded == [target["contact_url"]]
        item, token, guest, _ = send(client, intent="greeting")
        endpoint = f"/api/v1/contacts/{item['request_id']}/decision"
        assert client.post(endpoint, headers=headers, json={"action": "report"}).json()["reported"]
        assert (
            client.post(
                endpoint, headers=headers, json={"action": "reply", "body": "later"}
            ).status_code
            == 409
        )
        assert (
            client.get(
                f"/api/v1/public/contact/requests/{item['request_id']}", headers=guest
            ).json()["status"]
            == "declined"
        )
        client.put(
            "/api/v1/contacts/preferences", headers=headers, json={"enabled": False}
        ).raise_for_status()
        assert client.get("/api/v1/public/contact/qr?username=receiver").status_code == 404


def test_expired_guest_cannot_read_reply_and_recipient_cannot_request_on_sender_behalf(
    settings, database
):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, _, headers = setup_receiver(client)
        item, token, guest, _ = send(client, intent="greeting")
        cid = item["request_id"]
        endpoint = f"/api/v1/contacts/{cid}/decision"
        assert (
            client.post(
                endpoint, headers=headers, json={"action": "request_collaboration"}
            ).status_code
            == 404
        )
        client.post(
            endpoint, headers=headers, json={"action": "reply", "body": "private reply"}
        ).raise_for_status()
        with database.session_factory() as session:
            session.get(ContactRequest, UUID(cid)).expires_at = utc_now() - timedelta(seconds=1)
            session.commit()
        receipt = client.get(f"/api/v1/public/contact/requests/{cid}", headers=guest).json()
        assert receipt["status"] == "expired" and receipt["reply"] is None


def test_context_search_and_inbox_discovery_remain_readonly_and_scoped(settings, database):
    from agentpost.tasks.models import Friendship

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        receiver, agent, headers = setup_receiver(client)
        item, token, guest, _ = send(client)
        inbox = client.get("/api/v1/inbox", headers={"Authorization": f"Bearer {agent['api_key']}"})
        assert inbox.status_code == 200, inbox.text
        assert inbox.json()["pending_contact_count"] == 1
        endpoint = f"/api/v1/contacts/{item['request_id']}/decision"
        client.post(endpoint, headers=headers, json={"action": "accept"}).raise_for_status()
        _, sender_agent, sender_headers = setup_receiver(client, "search-sender")
        claimed = client.post(
            "/api/v1/contacts/claim", headers=sender_headers, json={"token": token}
        ).json()
        task_id = claimed["task_id"]
        context = client.get(f"/api/v1/tasks/{task_id}/context", params={"query": "具体情况"})
        assert context.status_code == 200, context.text
        data = context.json()
        assert len(data["sources"]) == 1 and data["sources"][0]["excerpt"].startswith("<script>")
        assert data["sources"][0]["activity_id"] in data["sources"][0]["source_url"]
        assert (
            client.get(f"/api/v1/tasks/{task_id}/context", params={"query": "%"}).json()["sources"]
            == []
        )
        assert (
            client.get(
                f"/api/v1/tasks/{task_id}/context", params={"before": str(uuid4())}
            ).status_code
            == 404
        )
        via_agent = client.get(
            f"/api/v1/agent/tasks/{task_id}/context",
            headers={"Authorization": f"Bearer {sender_agent['api_key']}"},
        )
        assert via_agent.status_code == 200
        _register(client, "context-outsider")
        _login(client, "context-outsider")
        assert client.get(f"/api/v1/tasks/{task_id}/context").status_code == 404
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Friendship)) == 1
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 2


def test_summary_provenance_review_and_human_continuation_revoke_old_lease(settings, database):
    from agentpost.tasks.models import TaskAssignment

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        _, agent, headers = setup_receiver(client)
        item, token, _, _ = send(client)
        client.post(
            f"/api/v1/contacts/{item['request_id']}/decision",
            headers=headers,
            json={"action": "accept"},
        ).raise_for_status()
        _, _, sender_headers = setup_receiver(client, "summary-sender")
        task_id = client.post(
            "/api/v1/contacts/claim", headers=sender_headers, json={"token": token}
        ).json()["task_id"]
        data = client.get(f"/api/v1/tasks/{task_id}/context").json()
        source = data["sources"][0]["activity_id"]
        payload = {
            "conclusions": "附件可直接阅读",
            "open_questions": "手机待复测",
            "next_steps": "完成手机测试",
            "source_activity_ids": [source],
            "based_on_activity_id": source,
            "confirmed": True,
        }
        assert (
            client.post(
                f"/api/v1/tasks/{task_id}/context-summary", headers=sender_headers, json=payload
            ).status_code
            == 403
        )
        agent_headers = {"Authorization": f"Bearer {agent['api_key']}"}
        assert (
            client.post(
                f"/api/v1/agent/tasks/{task_id}/context-summary",
                headers=agent_headers,
                json=payload,
            ).status_code
            == 403
        )
        draft = client.post(
            f"/api/v1/agent/tasks/{task_id}/context-summary",
            headers=agent_headers,
            json={**payload, "confirmed": False},
        )
        assert draft.status_code == 200, draft.text
        headers = {"X-CSRF-Token": _login(client, "receiver")}
        assert (
            client.post(
                f"/api/v1/tasks/{task_id}/context-summary",
                headers=headers,
                json={**payload, "source_activity_ids": [str(uuid4())]},
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/tasks/{task_id}/context-summary", headers=headers, json=payload
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/tasks/{task_id}/context").json()["summary"]["confirmed"]
        client.post(
            f"/api/v1/agent/tasks/{task_id}/context-summary",
            headers=agent_headers,
            json={**payload, "confirmed": False, "conclusions": "新增待确认想法"},
        ).raise_for_status()
        summaries = client.get(f"/api/v1/tasks/{task_id}/context").json()
        assert not summaries["summary"]["confirmed"]
        assert summaries["confirmed_summary"]["conclusions"] == "附件可直接阅读"
        assert (
            client.post(
                f"/api/v1/tasks/{task_id}/context-summary",
                headers=headers,
                json={**payload, "conclusions": " ", "open_questions": "", "next_steps": ""},
            ).status_code
            == 422
        )
        claim = client.post(
            "/api/v1/task-runs/claim", headers=agent_headers, json={"task_id": task_id}
        )
        assert claim.status_code == 200, claim.text
        run = claim.json()
        operation = {
            "action": "complete",
            "body": "Human 已补交结果，等待整项任务正式提交验收。",
            "operation_id": str(uuid4()),
        }
        endpoint = f"/api/v1/tasks/{task_id}/assignments/{run['assignment_id']}/continue"
        result = client.post(endpoint, headers=headers, json=operation)
        assert result.status_code == 200, result.text
        assert client.post(endpoint, headers=headers, json=operation).status_code == 200
        assert (
            client.post(
                endpoint, headers=headers, json={**operation, "body": "改写重放"}
            ).status_code
            == 409
        )
        stale = client.post(
            f"/api/v1/task-runs/{run['run_id']}/heartbeat",
            headers=agent_headers,
            json={"lease_token": run["lease_token"], "status": "running"},
        )
        assert stale.status_code == 404, stale.text
        assert client.get(f"/api/v1/tasks/{task_id}/context").json()["summary"]["stale"]
        with database.session_factory() as session:
            work = session.get(TaskAssignment, UUID(run["assignment_id"]))
            assert work.status == "completed" and work.result_status is None
            assert session.get(Task, UUID(task_id)).status == "active"


def test_work_reassignment_keeps_human_and_invalidates_old_run(settings, database):
    from agentpost.tasks.models import TaskAgentParticipant, TaskAssignment

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        person, agent, headers = setup_receiver(client)
        item, token, _, _ = send(client)
        client.post(
            f"/api/v1/contacts/{item['request_id']}/decision",
            headers=headers,
            json={"action": "accept"},
        ).raise_for_status()
        _, _, other = setup_receiver(client, "switch-sender")
        task_id = client.post(
            "/api/v1/contacts/claim", headers=other, json={"token": token}
        ).json()["task_id"]
        replacement = _create_owned_agent(
            client, human_id=person["user"]["id"], handle="replacement"
        )
        with database.session_factory() as session:
            session.add(
                TaskAgentParticipant(
                    task_id=UUID(task_id),
                    agent_id=UUID(replacement["agent"]["id"]),
                    human_user_id=UUID(person["user"]["id"]),
                    role="support",
                )
            )
            session.commit()
        headers = {"X-CSRF-Token": _login(client, "receiver")}
        auth = {"Authorization": f"Bearer {agent['api_key']}"}
        leased = client.post(
            "/api/v1/task-runs/claim", headers=auth, json={"task_id": task_id}
        ).json()
        payload = {
            "action": "reassign",
            "agent_id": replacement["agent"]["id"],
            "body": "从原进展接续",
            "operation_id": str(uuid4()),
        }
        endpoint = f"/api/v1/tasks/{task_id}/assignments/{leased['assignment_id']}/continue"
        result = client.post(endpoint, headers=headers, json=payload)
        assert result.status_code == 200, result.text
        assert client.post(endpoint, headers=headers, json=payload).status_code == 200
        with database.session_factory() as session:
            work = session.get(TaskAssignment, UUID(leased["assignment_id"]))
            assert str(work.responsible_human_user_id) == person["user"]["id"]
            assert str(work.assignee_agent_id) == replacement["agent"]["id"]
            assert (
                len(
                    list(session.scalars(select(AgentRun).where(AgentRun.assignment_id == work.id)))
                )
                == 2
            )
        assert (
            client.post(
                f"/api/v1/task-runs/{leased['run_id']}/heartbeat",
                headers=auth,
                json={"lease_token": leased["lease_token"], "status": "running"},
            ).status_code
            == 404
        )


def test_name_discovery_requires_choice_and_keeps_private_people_hidden(settings, database):
    from agentpost.control.models import HumanUser

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        first, _, _ = setup_receiver(client, "mars-one")
        second, _, _ = setup_receiver(client, "mars-two")
        hidden = _register(client, "mars-private")
        with database.session_factory() as session:
            for person in (first, second, hidden):
                session.get(HumanUser, UUID(person["user"]["id"])).display_name = "Mars Lee"
            session.commit()
        result = client.get("/api/v1/public/contact/resolve", params={"username": "Mars Lee"})
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["status"] == "needs_clarification"
        assert {c["username"] for c in data["candidates"]} == {"mars-one", "mars-two"}
        assert all(
            set(c) == {"username", "display_name", "introduction", "contact_url"}
            for c in data["candidates"]
        )
        partial = client.get("/api/v1/public/contact/resolve", params={"username": "mars"}).json()
        assert partial["status"] == "needs_clarification"
        exact = client.get("/api/v1/public/contact/resolve", params={"username": "mars-one"}).json()
        assert exact["status"] == "resolved"
        assert exact["username"] == "mars-one"
        assert (
            client.get("/api/v1/public/contact/resolve", params={"username": "%"}).status_code
            == 404
        )
        assert (
            client.get("/api/v1/public/contact/resolve", params={"username": " "}).status_code
            == 422
        )
        # Logged-in Human can find an exact display name and chooses a specific username.
        friends = client.get("/api/v1/friends/suggestions", params={"query": "Mars Lee"})
        assert friends.status_code == 200
        assert {c["username"] for c in friends.json()["items"]} == {"mars-one", "mars-two"}
        with database.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(ContactRequest)) == 0
            assert session.scalar(select(func.count()).select_from(Task)) == 0


def test_default_contact_enabled_without_preference_and_explicit_close_preserved(
    settings, database
):
    from agentpost.contacts.models import ContactPreference

    with TestClient(create_app(settings=_runtime(settings), database=database)) as client:
        person, _, headers = setup_receiver(client, save_preference=False)
        assert client.get("/api/v1/contacts/preferences").json()["enabled"] is True
        assert client.get("/api/v1/public/contact/resolve?username=receiver").status_code == 200
        assert (
            client.get("/api/v1/public/contact/resolve?username=receiv").json()["status"]
            == "needs_clarification"
        )
        send(client, intent="greeting")
        with database.session_factory() as session:
            assert session.get(ContactPreference, UUID(person["user"]["id"])) is None
            assert session.scalar(select(func.count()).select_from(Task)) == 0
            assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        client.put(
            "/api/v1/contacts/preferences", headers=headers, json={"enabled": False}
        ).raise_for_status()
        assert client.get("/api/v1/contacts/preferences").json()["enabled"] is False
        assert client.get("/api/v1/public/contact/resolve?username=receiver").status_code == 404
        assert client.get("/api/v1/public/contact/resolve?username=receiv").status_code == 404
        response = client.post(
            "/api/v1/public/contact/requests",
            headers={"Authorization": "Bearer gc_" + secrets.token_urlsafe(32)},
            json={
                "username": "receiver",
                "sender_name": "guest",
                "subject": "hello",
                "body": "hi",
                "intent": "greeting",
            },
        )
        assert response.status_code == 404
        assert client.get("/api/v1/contacts/preferences").json()["enabled"] is False
