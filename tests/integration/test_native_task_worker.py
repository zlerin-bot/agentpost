import os

import httpx
import pytest
from agentpost_sdk import AgentPost
from agentpost_sdk.task_worker import TaskRunWorker, codex_execute
from fastapi.testclient import TestClient
from test_task_collaboration import _create_owned_agent, _register, _runtime

from agentpost.main import create_app


@pytest.mark.skipif(
    os.environ.get("AGENTPOST_NATIVE_HOST_TEST") != "1", reason="native Codex test is opt-in"
)
def test_native_codex_task_round_trip(settings, database, tmp_path):
    with TestClient(create_app(settings=_runtime(settings), database=database)) as http:
        owner = _register(http, "native-worker")
        agent = _create_owned_agent(http, human_id=owner["user"]["id"], handle="native-worker")
        auth = {"Authorization": f"Bearer {agent['api_key']}"}
        task = http.post(
            "/api/v1/agent/tasks",
            headers={**auth, "Idempotency-Key": "native"},
            json={
                "title": "Synthetic native wake test",
                "goal": "Do not use tools. Return exactly AGENTPOST_WAKE_OK.",
                "expected_output": "AGENTPOST_WAKE_OK",
            },
        ).json()
        workspace = tmp_path / "empty-workspace"
        workspace.mkdir()

        def transport(request):
            response = http.request(
                request.method,
                str(request.url),
                headers=dict(request.headers),
                content=request.content,
            )
            return httpx.Response(
                response.status_code, headers=dict(response.headers), content=response.content
            )

        with AgentPost(
            "http://testserver", agent["api_key"], transport=httpx.MockTransport(transport)
        ) as client:
            worker = TaskRunWorker(
                client,
                state_dir=tmp_path / "journal",
                identity="synthetic-native",
                execute=lambda claim, heartbeat: codex_execute(
                    claim, workspace=workspace, heartbeat=heartbeat, timeout=120
                ),
            )
            result = worker.once(task["task_id"])
            assert result["status"] == "result_recorded"
            detail = client.get_task(task["task_id"])
            assert any(a["result_status"] == "completed" for a in detail.assignments)
            assert not worker.path.exists()
            print("native_run_id=" + result["run_id"])
