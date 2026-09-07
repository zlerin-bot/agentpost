import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from agentpost_sdk.errors import ConfigurationError, TransportError
from agentpost_sdk.task_worker import TaskRunWorker, codex_execute


def test_lost_result_receipt_retries_without_reexecuting(tmp_path):
    task, run = str(uuid4()), str(uuid4())
    claim = {"task_id": task, "run_id": run, "lease_token": "private-lease"}
    executions, submissions = [], []

    def complete(*a, **kw):
        submissions.append(kw)
        if len(submissions) == 1:
            raise TransportError("response lost")
        return {"status": "completed", "replayed": True}

    api = SimpleNamespace(
        pending=lambda **kw: {"items": [{"assignment_id": str(uuid4())}]},
        claim=lambda **kw: claim,
        complete=complete,
    )

    def execute(claim, heartbeat):
        executions.append(claim)
        return {"status": "completed", "summary": "fixture result"}

    client = SimpleNamespace(task_runs=api)
    worker = TaskRunWorker(client, state_dir=tmp_path, identity="same-agent", execute=execute)
    with pytest.raises(TransportError):
        worker.once(task)
    assert len(executions) == 1
    if os.name != "nt":
        assert worker.path.stat().st_mode & 0o077 == 0
    restarted = TaskRunWorker(client, state_dir=tmp_path, identity="same-agent", execute=execute)
    assert restarted.once(task)["status"] == "result_recorded"
    assert len(executions) == 1
    assert submissions[0]["idempotency_key"] == submissions[1]["idempotency_key"]
    assert not worker.path.exists()


def test_interrupted_run_never_silently_restarts(tmp_path):
    task = str(uuid4())
    worker = TaskRunWorker(None, state_dir=tmp_path, identity="agent", execute=None)
    worker._save({"phase": "running", "claim": {"task_id": task}})
    with pytest.raises(ConfigurationError, match="requires_review"):
        worker.once(task)
    foreign = TaskRunWorker(None, state_dir=tmp_path, identity="other", execute=None)
    with pytest.raises(ConfigurationError, match="identity_mismatch"):
        foreign.once(task)


def test_codex_adapter_reads_real_subprocess_events_without_leaking_lease(tmp_path, monkeypatch):
    executable = tmp_path / "codex-fixture"
    session = str(uuid4())
    executable.write_text(f'''#!{Path(sys.executable).resolve()}
import json,sys,os
payload=sys.stdin.read()
assert "private-lease" not in payload
assert "AGENTPOST_API_KEY" not in os.environ
print(json.dumps({{"type":"thread.started","thread_id":"{session}"}}))
print(json.dumps({{"type":"turn.started"}}))
result = {{"status":"completed","summary":"fixture result"}}
item = {{"type":"agent_message","text":json.dumps(result)}}
print(json.dumps({{"type":"item.completed","item":item}}))
print(json.dumps({{"type":"turn.completed"}}))
''')
    executable.chmod(0o700)
    monkeypatch.setattr("agentpost_sdk.task_worker.shutil.which", lambda _: str(executable))
    monkeypatch.setenv("AGENTPOST_API_KEY", "not-for-host")
    beats = []
    result = codex_execute(
        {"lease_token": "private-lease", "instruction": "test"},
        workspace=tmp_path,
        heartbeat=lambda session, awake=False: beats.append((session, awake)),
    )
    assert result["summary"] == "fixture result"
    assert beats == [(session, False), (session, True)]
    assert result["checkpoint"]["local_session_id"] == session
