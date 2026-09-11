from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from agentpost_mcp.config import Settings
from agentpost_mcp.results import failure, success
from agentpost_mcp.server import create_server
from agentpost_sdk import ConfigurationError, ConnectorCredential, ProtocolError
from mcp import Client


class FakeClient:
    def __init__(self, calls: list[tuple[str, object]]) -> None:
        self.calls = calls
        self.inbox = SimpleNamespace(list=self._inbox)
        self.messages = SimpleNamespace(
            get=self._get,
            ack=self._ack,
            reply=self._reply,
        )
        self.task_runs = SimpleNamespace(
            claim=self._claim_task_run,
            heartbeat=self._heartbeat_task_run,
            complete=self._complete_task_run,
        )

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.calls.append(("close", None))

    def send(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append(("send", (args, kwargs)))
        return {"message_id": "msg_sent", "content": {"body": "external"}}

    def resolve_recipient(self, query: str) -> dict[str, object]:
        self.calls.append(("resolve", query))
        return {
            "status": "resolved",
            "query": query,
            "match": {"address": "bob@agents.local", "display_label": "Bob's Codex"},
            "candidates": [],
        }

    def resolve_task(self, query: str) -> dict[str, object]:
        self.calls.append(("resolve_task", query))
        return {
            "status": "resolved",
            "query": query,
            "match": {
                "task_id": "33333333-3333-3333-3333-333333333333",
                "title": "小孔成像",
            },
            "candidates": [],
        }

    def get_task(self, task_id: UUID) -> dict[str, object]:
        self.calls.append(("get_task", task_id))
        return {"task_id": str(task_id), "title": "小孔成像"}

    def task_briefing(self, task_id: UUID, **kwargs: object) -> dict[str, object]:
        self.calls.append(("task_briefing", (task_id, kwargs)))
        return {"task_id": str(task_id), "my_work": [], "security_label": "external_agent_content"}

    def send_task_message(self, task_id: UUID, body: object, **kwargs: object):
        self.calls.append(("send_task_message", (task_id, body, kwargs)))
        return {"task_id": str(task_id), "activity_id": str(task_id)}

    def _inbox(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("inbox", kwargs))
        return {"items": [], "next_cursor": kwargs.get("cursor"), "has_more": False}

    def _get(self, message_id: str) -> dict[str, object]:
        self.calls.append(("get", message_id))
        return {"message_id": message_id}

    def _ack(self, message_id: str) -> dict[str, object]:
        self.calls.append(("ack", message_id))
        return {"message_id": message_id}

    def _reply(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append(("reply", (args, kwargs)))
        return {"message_id": "msg_reply"}

    def search_agents(self, **kwargs: object) -> list[dict[str, str]]:
        self.calls.append(("search", kwargs))
        return [{"address": "bob@agents.local"}]

    def _claim_task_run(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("claim_task_run", kwargs))
        return {"run_id": "11111111-1111-1111-1111-111111111111", "lease_token": "x" * 24}

    def _heartbeat_task_run(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls.append(("heartbeat_task_run", (args, kwargs)))
        return {"run_id": str(args[0]), "lease_token": kwargs["lease_token"]}

    def _complete_task_run(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("complete_task_run", (args, kwargs)))


@pytest.fixture
def adapter() -> tuple[object, list[tuple[str, object]]]:
    calls: list[tuple[str, object]] = []
    server = create_server(
        Settings("http://example.test", "agt_secret", 30, "WARNING"),
        create_client=lambda: FakeClient(calls),
    )
    return server, calls


@pytest.mark.anyio
async def test_v2_tool_contract_and_calls(adapter: tuple[object, list[tuple[str, object]]]) -> None:
    server, calls = adapter
    async with Client(server) as client:  # type: ignore[arg-type]
        listed = await client.list_tools()
        assert [tool.name for tool in listed.tools] == [
            "agentpost_resolve_recipient",
            "agentpost_resolve_task",
            "agentpost_handshake",
            "agentpost_get_task",
            "agentpost_task_briefing",
            "agentpost_task_activities",
            "agentpost_send_task_text",
            "agentpost_send_task_message",
            "agentpost_list_inbox",
            "agentpost_read_message",
            "agentpost_reply",
            "agentpost_ack",
            "agentpost_search_directory",
            "agentpost_list_pending_task_runs",
            "agentpost_claim_task_run",
            "agentpost_update_task_run",
            "agentpost_complete_task_run",
            "agentpost_runtime_status",
            "agentpost_upload_attachment",
            "agentpost_download_attachment",
        ]
        annotations = listed.tools[0].annotations
        assert annotations is not None
        assert annotations.read_only_hint is True
        assert annotations.open_world_hint is True

        resolved = await client.call_tool(
            "agentpost_resolve_recipient",
            {"query": "send this to Bob's Codex"},
        )
        assert resolved.structured_content["data"]["match"]["address"] == "bob@agents.local"

        resolved_task = await client.call_tool(
            "agentpost_resolve_task",
            {"query": "小孔成像"},
        )
        assert (
            resolved_task.structured_content["data"]["match"]["task_id"]
            == "33333333-3333-3333-3333-333333333333"
        )
        task_id = "33333333-3333-3333-3333-333333333333"
        context = await client.call_tool("agentpost_get_task", {"task_id": task_id})
        assert context.structured_content["data"]["title"] == "小孔成像"
        task_message = await client.call_tool(
            "agentpost_send_task_message",
            {"task_id": task_id, "body": "请继续协同"},
        )
        assert task_message.structured_content["data"]["task_id"] == task_id

        page = await client.call_tool("agentpost_list_inbox", {"cursor": "opaque+/="})
        assert page.structured_content["data"]["next_cursor"] == "opaque+/="
        await client.call_tool("agentpost_read_message", {"message_id": "msg_1"})
        await client.call_tool("agentpost_reply", {"message_id": "msg_1", "body": "done"})
        await client.call_tool("agentpost_ack", {"message_id": "msg_1"})
        directory = await client.call_tool("agentpost_search_directory", {"q": "bank"})
        assert directory.structured_content["data"][0]["address"] == "bob@agents.local"
        claimed = await client.call_tool("agentpost_claim_task_run", {})
        assert claimed.structured_content["data"]["lease_token"] == "x" * 24
        await client.call_tool(
            "agentpost_update_task_run",
            {
                "run_id": "11111111-1111-1111-1111-111111111111",
                "lease_token": "x" * 24,
                "status": "running",
            },
        )
        await client.call_tool(
            "agentpost_complete_task_run",
            {
                "run_id": "11111111-1111-1111-1111-111111111111",
                "lease_token": "x" * 24,
                "status": "completed",
                "summary": "done",
            },
        )

    assert [call[0] for call in calls].count("close") == 12
    assert ("resolve", "send this to Bob's Codex") in calls
    assert ("resolve_task", "小孔成像") in calls
    assert ("get", "msg_1") in calls


def test_api_key_is_excluded_from_settings_repr() -> None:
    settings = Settings("http://example.test", "agt_top_secret", 30, "WARNING")
    assert "agt_top_secret" not in repr(settings)


class MemoryCredentialStore:
    def __init__(self, credential: ConnectorCredential | None) -> None:
        self.credential = credential
        self.loads: list[tuple[str, str]] = []

    def load(self, *, server: str, profile: str) -> ConnectorCredential | None:
        self.loads.append((server, profile))
        return self.credential


def test_settings_load_exact_connector_profile_from_os_store(monkeypatch) -> None:
    monkeypatch.delenv("AGENTPOST_API_KEY", raising=False)
    monkeypatch.setenv("AGENTPOST_SERVER", " https://agentpost.me/ ")
    monkeypatch.setenv("AGENTPOST_PROFILE", "codex:mars-mac")
    credential = ConnectorCredential(
        server="https://agentpost.me",
        profile="codex:mars-mac",
        connector_id="con_codex",
        agent_address="mars@agentpost.me",
        api_key="agt_vault_secret",
    )
    store = MemoryCredentialStore(credential)

    settings = Settings.from_env(credential_store=store)

    assert settings.server == "https://agentpost.me"
    assert settings.api_key == "agt_vault_secret"
    assert store.loads == [("https://agentpost.me", "codex:mars-mac")]
    assert "agt_vault_secret" not in repr(settings)


def test_settings_reject_ambiguous_or_missing_identity_source(monkeypatch) -> None:
    monkeypatch.setenv("AGENTPOST_API_KEY", "agt_explicit")
    monkeypatch.setenv("AGENTPOST_PROFILE", "codex:mars-mac")
    store = MemoryCredentialStore(None)

    with pytest.raises(ConfigurationError, match="mutually exclusive"):
        Settings.from_env(credential_store=store)
    assert store.loads == []

    monkeypatch.delenv("AGENTPOST_API_KEY")
    with pytest.raises(ConfigurationError, match="No OS credential was found"):
        Settings.from_env(credential_store=store)
    assert store.loads == [("http://127.0.0.1:8000", "codex:mars-mac")]

    monkeypatch.delenv("AGENTPOST_PROFILE")
    with pytest.raises(ConfigurationError, match="API_KEY or AGENTPOST_PROFILE is required"):
        Settings.from_env(credential_store=store)


def test_external_business_payload_is_opaque_while_reserved_top_level_fields_are_removed() -> None:
    result = success(
        {
            "content": {"body": {"token": "business vocabulary", "secret": "opaque data"}},
            "metadata": {"storage_key": "business field", "password": "business field"},
            "storage_key": "server-internal-object-key",
            "api_key": "server-internal-secret",
        },
        external=True,
    )

    assert result.structured_content is not None
    data = result.structured_content["data"]
    assert data["content"]["body"] == {
        "token": "business vocabulary",
        "secret": "opaque data",
    }
    assert data["metadata"] == {
        "storage_key": "business field",
        "password": "business field",
    }
    assert "storage_key" not in data
    assert "api_key" not in data
    assert result.structured_content["security_label"] == "external_agent_content"


def test_mutating_protocol_failure_is_retryable_with_same_key_and_sanitized_request_id() -> None:
    result = failure(
        ProtocolError(
            "malformed",
            status_code=201,
            code="MALFORMED_RESPONSE",
            request_id="agt_secret_must_not_escape",
            idempotency_key="mcp-reuse-this-key",
        ),
        operation="send",
    )

    assert result.structured_content is not None
    error = result.structured_content["error"]
    assert error["code"] == "AGENTPOST_PROTOCOL_ERROR"
    assert error["retryable"] is True
    assert error["acceptance_unknown"] is True
    assert error["idempotency_key"] == "mcp-reuse-this-key"
    assert "request_id" not in error


@pytest.mark.anyio
async def test_portable_task_schema_preserves_body_and_wakeup_fields(adapter):
    server, calls = adapter
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        body_schema = tools["agentpost_send_task_message"].input_schema["properties"]["body"]
        assert "$ref" not in body_schema
        assert any(item.get("type") == "string" for item in body_schema["anyOf"])
        update = tools["agentpost_update_task_run"].input_schema["properties"]
        assert update["checkpoint"]["type"] == "object"
        assert update["wake_status"]["type"] == "string"
        assert update["local_session_id"]["type"] == "string"
        await client.call_tool(
            "agentpost_send_task_message",
            {
                "task_id": "33333333-3333-3333-3333-333333333333",
                "body": {"nested": ["测试", {"ok": True}]},
                "content_format": "json",
            },
        )
        assert next(c[1][1] for c in calls if c[0] == "send_task_message") == {
            "nested": ["测试", {"ok": True}]
        }
        status = await client.call_tool("agentpost_runtime_status", {})
        from agentpost_sdk import __version__

        assert status.structured_content["data"]["runtime_version"] == __version__


@pytest.mark.anyio
async def test_local_attachment_tools_reject_relative_and_existing_paths(adapter, tmp_path):
    server, calls = adapter
    target = tmp_path / "keep.txt"
    target.write_text("keep")
    async with Client(server) as client:
        uploaded = await client.call_tool("agentpost_upload_attachment", {"path": "relative.txt"})
        assert uploaded.is_error
        downloaded = await client.call_tool(
            "agentpost_download_attachment",
            {
                "attachment_id": "33333333-3333-3333-3333-333333333333",
                "destination": str(target),
                "expected_sha256": "a" * 64,
            },
        )
        assert downloaded.is_error
        assert target.read_text() == "keep"
        assert not calls


@pytest.mark.anyio
async def test_text_entry_forwards_reply_attachments_and_idempotency(adapter):
    server, calls = adapter
    identifier = "33333333-3333-3333-3333-333333333333"
    async with Client(server) as client:
        response = await client.call_tool(
            "agentpost_send_task_text",
            {
                "task_id": identifier,
                "body": "兼容正文",
                "attachment_ids": [identifier],
                "reply_to_activity_id": identifier,
                "referenced_activity_ids": [identifier],
                "idempotency_key": "compat-test",
                "publication_origin": "human_delegated",
            },
        )
        assert not response.is_error
        invocation = [args for name, args in calls if name == "send_task_message"][-1]
        assert invocation[1] == "兼容正文"
        assert invocation[2]["idempotency_key"] == "compat-test"
        assert invocation[2]["attachments"] == [UUID(identifier)]
        assert invocation[2]["reply_to_activity_id"] == UUID(identifier)
        invalid = await client.call_tool(
            "agentpost_send_task_text",
            {"task_id": identifier, "body": "invalid", "reply_to_activity_id": "not-a-uuid"},
        )
        assert invalid.is_error


@pytest.mark.anyio
async def test_briefing_tool_forwards_scoped_cursors(adapter):
    server, calls = adapter
    task_id = "33333333-3333-3333-3333-333333333333"
    async with Client(server) as client:
        result = await client.call_tool(
            "agentpost_task_briefing",
            {
                "task_id": task_id,
                "cursor": "source-cursor",
                "assignment_cursor": "work-cursor",
                "limit": 3,
            },
        )
        assert not result.is_error
    assert (
        "task_briefing",
        (
            UUID(task_id),
            {"cursor": "source-cursor", "assignment_cursor": "work-cursor", "limit": 3},
        ),
    ) in calls
