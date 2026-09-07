from __future__ import annotations

from datetime import UTC, datetime, timedelta


def heartbeat_timeout_seconds(interval_seconds: int) -> int:
    """Allow three missed heartbeats, with a one-minute minimum grace period."""

    return max(60, interval_seconds * 3)


def connector_connection_state(
    connector: object | None,
    *,
    now: datetime,
    heartbeat_interval_seconds: int,
) -> str:
    if connector is None:
        return "disconnected"
    if getattr(connector, "status", None) != "active":
        return "connection_error"
    if getattr(connector, "health_status", None) == "error" or getattr(
        connector,
        "last_error_code",
        None,
    ):
        return "connection_error"
    heartbeat = getattr(connector, "last_heartbeat_at", None)
    if heartbeat is None:
        return "awaiting_agent"
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    else:
        heartbeat = heartbeat.astimezone(UTC)
    timeout = timedelta(seconds=heartbeat_timeout_seconds(heartbeat_interval_seconds))
    if now.astimezone(UTC) - heartbeat > timeout:
        return "offline"
    return "connected"


def agent_work_availability(
    connector: object | None,
    *,
    now: datetime,
    heartbeat_interval_seconds: int,
    has_active_run: bool = False,
) -> str:
    """Human-facing availability derived only from current server evidence."""

    if has_active_run:
        return "working"
    if (
        connector_connection_state(
            connector,
            now=now,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        != "connected"
    ):
        return "needs_attention"
    listener_heartbeat = getattr(connector, "task_listener_last_heartbeat_at", None)
    if listener_heartbeat is not None:
        if listener_heartbeat.tzinfo is None:
            listener_heartbeat = listener_heartbeat.replace(tzinfo=UTC)
        else:
            listener_heartbeat = listener_heartbeat.astimezone(UTC)
    timeout = timedelta(seconds=heartbeat_timeout_seconds(heartbeat_interval_seconds))
    listening = (
        getattr(connector, "task_listener_status", None) == "listening"
        and listener_heartbeat is not None
        and now.astimezone(UTC) - listener_heartbeat <= timeout
    )
    return "ready" if listening else "needs_attention"
