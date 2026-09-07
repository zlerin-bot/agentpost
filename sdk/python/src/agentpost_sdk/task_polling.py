"""Bounded incremental polling for a host-owned loop, with durable processing cursors.

The host owns wake-up and execution. This module never starts a model, claims a Run,
ACKs a message, or interprets activity content as instructions.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from agentpost_sdk.client import AgentPost
from agentpost_sdk.errors import ConfigurationError, ResponseError, TransportError


class TaskPoller:
    def __init__(self, client: AgentPost, *, state_path: Path, agent_id: str) -> None:
        self.client = client
        self.path = state_path
        self.identity = f"{client.server}:{UUID(agent_id)}"
        self.cursors: dict[str, str] = {}
        if state_path.exists():
            data = json.loads(state_path.read_text())
            if data.get("identity") != self.identity:
                raise ConfigurationError("polling state belongs to another connection")
            self.cursors = data["cursors"]

    def poll_once(self, task_id: str, consume: Callable[[dict], None], *, limit: int = 50) -> dict:
        """Process one page; checkpoint only after successful consumption.

        Consumer must be idempotent by activity_id: a crash before cursor save can replay.
        Exactly one host loop must own a state file. Use separate files for independent consumers.
        """
        task_id = str(UUID(task_id))
        page = self.client.task_activities(
            task_id, cursor=self.cursors.get(task_id, ""), limit=limit
        )
        for item in page["items"]:
            consume(item)
        cursor = page.get("next_cursor")
        if cursor and cursor != self.cursors.get(task_id):
            updated = {**self.cursors, task_id: str(UUID(cursor))}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".agentpost-cursor-", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump({"identity": self.identity, "cursors": updated}, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            self.cursors = updated
        return {"processed": len(page["items"]), "has_more": page["has_more"], "cursor": cursor}

    def run(
        self,
        task_ids: list[str],
        consume: Callable[[dict], None],
        *,
        stop,
        interval: float = 30,
        max_backoff: float = 300,
    ) -> None:
        """Host-owned stoppable loop, fair one-page polling and bounded transport backoff.

        No background thread is created. Host calls this in its managed service and supplies
        stop.wait/stop.is_set. Non-retryable failures stop visibly; content is never executed.
        """
        if not task_ids or interval < 1 or max_backoff < interval:
            raise ConfigurationError("invalid polling schedule")
        task_ids = list(dict.fromkeys(str(UUID(task)) for task in task_ids))
        delay = interval
        while not stop.is_set():
            more = False
            try:
                for task_id in task_ids:
                    if stop.is_set():
                        return
                    more |= bool(self.poll_once(task_id, consume)["has_more"])
            except (TransportError, ResponseError) as exc:
                if isinstance(exc, ResponseError) and exc.status_code not in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    raise
                stop.wait(delay)
                delay = min(max_backoff, delay * 2)
                continue
            delay = interval
            stop.wait(1 if more else interval)
