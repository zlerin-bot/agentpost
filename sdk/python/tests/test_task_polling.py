from types import SimpleNamespace
from uuid import uuid4

import pytest
from agentpost_sdk import ConfigurationError
from agentpost_sdk.task_polling import TaskPoller


def test_cursor_survives_restart_only_after_consumption(tmp_path):
    task, agent, activity = map(str, (uuid4(), uuid4(), uuid4()))
    calls = []

    def page(task_id, **kwargs):
        calls.append(kwargs)
        return {"items": [{"activity_id": activity}], "next_cursor": activity, "has_more": False}

    client = SimpleNamespace(server="https://post.test", task_activities=page)
    path = tmp_path / "cursor.json"
    poller = TaskPoller(client, state_path=path, agent_id=agent)

    def fail(item):
        raise RuntimeError("host unavailable")

    with pytest.raises(RuntimeError):
        poller.poll_once(task, fail)
    assert not path.exists()
    received = []
    poller.poll_once(task, received.append)
    assert received == [{"activity_id": activity}]
    restarted = TaskPoller(client, state_path=path, agent_id=agent)
    restarted.poll_once(task, received.append)
    assert calls[-1]["cursor"] == activity
    with pytest.raises(ConfigurationError):
        TaskPoller(client, state_path=path, agent_id=str(uuid4()))


def test_transport_backoff_is_bounded_and_stoppable(tmp_path):
    from agentpost_sdk.errors import TransportError

    class Stop:
        def __init__(self):
            self.delays = []

        def is_set(self):
            return len(self.delays) >= 4

        def wait(self, delay):
            self.delays.append(delay)

    def unavailable(*args, **kwargs):
        raise TransportError("offline")

    client = SimpleNamespace(server="https://post.test", task_activities=unavailable)
    poller = TaskPoller(client, state_path=tmp_path / "state", agent_id=str(uuid4()))
    stop = Stop()
    poller.run([str(uuid4())], lambda item: None, stop=stop, interval=2, max_backoff=5)
    assert stop.delays == [2, 4, 5, 5]
    assert not (tmp_path / "state").exists()
