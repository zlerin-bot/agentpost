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


def setup_receiver(client, username="receiver"):
    person = _register(client, username)
    agent = _create_owned_agent(client, human_id=person["user"]["id"], handle=username)
    csrf = _login(client, username)
    headers = {"X-CSRF-Token": csrf}
    result = client.put(f"/api/v1/orbit/agents/{agent['agent']['id']}/default", headers=headers)
    assert result.status_code == 200, result.text
    result = client.put("/api/v1/contacts/preferences", headers=headers, json={"enabled": True})
    assert result.status_code == 200, result.text
    return person, agent, headers


def send(client, name="receiver", token=None):
    token = token or "gc_" + secrets.token_urlsafe(32)
    payload = {
        "username": name,
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
            "match": "exact",
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
