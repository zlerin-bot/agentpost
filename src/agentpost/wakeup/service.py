from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agentpost.accounts.crypto import decrypt_application_secret, encrypt_application_secret
from agentpost.config import Settings
from agentpost.control.models import AgentOwnership, HumanUser
from agentpost.identity.models import Agent, utc_now
from agentpost.onboarding.models import AgentConnectorBinding, ConnectorInstance
from agentpost.tasks.models import AgentRun, TaskAssignment
from agentpost.wakeup.models import AgentWakeChannel, AgentWakeDelivery
from agentpost.wakeup.schemas import FeishuAilyWakeChannelCreate, WakeChannelStatus


class WakeChannelNotFoundError(LookupError):
    pass


class WakeChannelAccessDeniedError(PermissionError):
    pass


class WakeChannelInvalidEndpointError(ValueError):
    pass


class WakeDeliveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


WakeSender = Callable[[str, str, dict[str, str]], None]


def _endpoint_parts(raw_url: str) -> tuple[str, str]:
    parts = urlsplit(raw_url.strip())
    try:
        port = parts.port
        hostname = parts.hostname.casefold() if parts.hostname else ""
        hostname.encode("ascii")
    except (UnicodeEncodeError, ValueError) as exc:
        raise WakeChannelInvalidEndpointError from exc
    if (
        parts.scheme != "https"
        or not hostname
        or port not in {None, 443}
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
        or hostname in {"localhost", "localhost.localdomain"}
    ):
        raise WakeChannelInvalidEndpointError
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise WakeChannelInvalidEndpointError
    return raw_url.strip(), hostname


def _assert_allowed_host(settings: Settings, hostname: str) -> None:
    allowed = settings.enabled_feishu_aily_wake_hosts
    if not allowed:
        return
    if any(
        hostname == pattern or (pattern.startswith("*.") and hostname.endswith(pattern[1:]))
        for pattern in allowed
    ):
        return
    raise WakeChannelInvalidEndpointError


def _owned_agent_connector(
    session: Session, *, user: HumanUser, agent_id: UUID
) -> tuple[Agent, ConnectorInstance | None]:
    ownership = session.get(AgentOwnership, agent_id)
    agent = session.get(Agent, agent_id)
    binding = session.get(AgentConnectorBinding, agent_id)
    connector = None
    if binding is not None:
        connector = session.get(ConnectorInstance, binding.connector_instance_id)
    if ownership is None or ownership.human_user_id != user.id or agent is None:
        raise WakeChannelAccessDeniedError
    return agent, connector


def _owned_feishu_connector(
    session: Session, *, user: HumanUser, agent_id: UUID
) -> tuple[Agent, ConnectorInstance]:
    agent, connector = _owned_agent_connector(session, user=user, agent_id=agent_id)
    if (
        connector is None
        or connector.status != "active"
        or connector.connector_type != "feishu_aily"
    ):
        raise WakeChannelAccessDeniedError
    return agent, connector


def _status(session: Session, channel: AgentWakeChannel, settings: Settings) -> WakeChannelStatus:
    endpoint = decrypt_application_secret(
        channel.encrypted_endpoint, settings.human_mfa_encryption_key
    )
    _, endpoint_host = _endpoint_parts(endpoint)
    pending = session.scalar(
        select(func.count())
        .select_from(AgentWakeDelivery)
        .where(
            AgentWakeDelivery.channel_id == channel.id,
            AgentWakeDelivery.status.in_(["pending", "sending"]),
        )
    )
    return WakeChannelStatus(
        channel_type=channel.channel_type,  # type: ignore[arg-type]
        status=channel.status,  # type: ignore[arg-type]
        endpoint_host=endpoint_host,
        last_tested_at=channel.last_tested_at,
        last_success_at=channel.last_success_at,
        last_error_code=channel.last_error_code,
        pending_deliveries=int(pending or 0),
    )


def get_wake_channel(
    session: Session, settings: Settings, *, user: HumanUser, agent_id: UUID
) -> WakeChannelStatus:
    _owned_agent_connector(session, user=user, agent_id=agent_id)
    channel = session.scalar(
        select(AgentWakeChannel).where(
            AgentWakeChannel.agent_id == agent_id,
            AgentWakeChannel.status != "disabled",
        )
    )
    if channel is None:
        raise WakeChannelNotFoundError
    return _status(session, channel, settings)


def _save_channel(
    session: Session,
    settings: Settings,
    *,
    user: HumanUser,
    agent_id: UUID,
    connector: ConnectorInstance | None,
    channel_type: str,
    payload: FeishuAilyWakeChannelCreate,
) -> WakeChannelStatus:
    endpoint, hostname = _endpoint_parts(payload.webhook_url.get_secret_value())
    _assert_allowed_host(settings, hostname)
    token = payload.bearer_token.get_secret_value().strip()
    if not token:
        raise WakeChannelInvalidEndpointError
    channel = session.scalar(select(AgentWakeChannel).where(AgentWakeChannel.agent_id == agent_id))
    if channel is None:
        channel = AgentWakeChannel(
            agent_id=agent_id,
            human_user_id=user.id,
            connector_instance_id=connector.id if connector else None,
            channel_type=channel_type,
            encrypted_endpoint="",
            encrypted_bearer_token="",
        )
        session.add(channel)
    channel.human_user_id = user.id
    channel.connector_instance_id = connector.id if connector else None
    channel.channel_type = channel_type
    channel.encrypted_endpoint = encrypt_application_secret(
        endpoint, settings.human_mfa_encryption_key
    )
    channel.encrypted_bearer_token = encrypt_application_secret(
        token, settings.human_mfa_encryption_key
    )
    channel.status = "configured"
    channel.last_tested_at = None
    channel.last_success_at = None
    channel.last_error_code = None
    channel.updated_at = utc_now()
    session.flush()
    _enqueue_existing_runs(session, channel=channel)
    return _status(session, channel, settings)


def configure_wake_channel(
    session: Session,
    settings: Settings,
    *,
    user: HumanUser,
    agent_id: UUID,
    payload: FeishuAilyWakeChannelCreate,
) -> WakeChannelStatus:
    _, connector = _owned_feishu_connector(session, user=user, agent_id=agent_id)
    result = _save_channel(
        session,
        settings,
        user=user,
        agent_id=agent_id,
        connector=connector,
        channel_type="feishu_aily_webhook",
        payload=payload,
    )
    connector.task_listener_status = "stopped"
    connector.task_listener_last_heartbeat_at = utc_now()
    connector.wake_capability = "manual"
    session.commit()
    return result


def configure_feishu_notification_channel(
    session: Session,
    settings: Settings,
    *,
    user: HumanUser,
    agent_id: UUID,
    payload: FeishuAilyWakeChannelCreate,
) -> WakeChannelStatus:
    _agent, connector = _owned_agent_connector(session, user=user, agent_id=agent_id)
    if connector is not None and connector.connector_type == "feishu_aily":
        raise WakeChannelAccessDeniedError
    result = _save_channel(
        session,
        settings,
        user=user,
        agent_id=agent_id,
        connector=None,
        channel_type="feishu_notification_webhook",
        payload=payload,
    )
    session.commit()
    return result


def disable_wake_channel(
    session: Session, settings: Settings, *, user: HumanUser, agent_id: UUID
) -> None:
    _, connector = _owned_agent_connector(session, user=user, agent_id=agent_id)
    channel = session.scalar(select(AgentWakeChannel).where(AgentWakeChannel.agent_id == agent_id))
    if channel is None or channel.status == "disabled":
        raise WakeChannelNotFoundError
    channel.status = "disabled"
    channel.updated_at = utc_now()
    if channel.channel_type == "feishu_aily_webhook" and connector is not None:
        connector.wake_capability = "manual"
        connector.task_listener_status = "stopped"
        connector.task_listener_last_heartbeat_at = utc_now()
    for delivery in session.scalars(
        select(AgentWakeDelivery).where(
            AgentWakeDelivery.channel_id == channel.id,
            AgentWakeDelivery.status.in_(["pending", "sending"]),
        )
    ):
        delivery.status = "cancelled"
        delivery.updated_at = utc_now()
    session.commit()


def enqueue_run_wake(
    session: Session,
    *,
    agent_id: UUID,
    task_id: UUID,
    assignment_id: UUID,
    run_id: UUID,
) -> None:
    channel = session.scalar(
        select(AgentWakeChannel).where(
            AgentWakeChannel.agent_id == agent_id,
            AgentWakeChannel.status.in_(["configured", "active", "error"]),
        )
    )
    if channel is None:
        return
    if (
        session.scalar(select(AgentWakeDelivery.id).where(AgentWakeDelivery.run_id == run_id))
        is not None
    ):
        return
    session.add(
        AgentWakeDelivery(
            channel_id=channel.id,
            agent_id=agent_id,
            task_id=task_id,
            assignment_id=assignment_id,
            run_id=run_id,
        )
    )
    session.flush()


def _enqueue_existing_runs(session: Session, *, channel: AgentWakeChannel) -> None:
    rows = session.execute(
        select(AgentRun, TaskAssignment)
        .join(TaskAssignment, TaskAssignment.id == AgentRun.assignment_id)
        .where(AgentRun.agent_id == channel.agent_id, AgentRun.status == "queued")
    ).all()
    existing = set(
        session.scalars(
            select(AgentWakeDelivery.run_id).where(
                AgentWakeDelivery.run_id.in_([run.id for run, _ in rows])
            )
        ).all()
    )
    for run, assignment in rows:
        if run.id not in existing:
            session.add(
                AgentWakeDelivery(
                    channel_id=channel.id,
                    agent_id=channel.agent_id,
                    task_id=assignment.task_id,
                    assignment_id=assignment.id,
                    run_id=run.id,
                )
            )


def _assert_public_dns(hostname: str) -> None:
    try:
        addresses = {
            result[4][0] for result in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise WakeDeliveryError("WAKE_DNS_UNAVAILABLE") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise WakeDeliveryError("WAKE_ENDPOINT_NOT_PUBLIC")


def send_webhook(endpoint: str, token: str, payload: dict[str, str]) -> None:
    _, hostname = _endpoint_parts(endpoint)
    _assert_public_dns(hostname)
    try:
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise WakeDeliveryError("WAKE_TRANSPORT_ERROR") from exc
    if response.is_redirect:
        raise WakeDeliveryError("WAKE_REDIRECT_REJECTED")
    if not 200 <= response.status_code < 300:
        raise WakeDeliveryError(f"WAKE_HTTP_{response.status_code}")
    try:
        result = response.json()
    except ValueError as exc:
        raise WakeDeliveryError("WAKE_INVALID_RESPONSE") from exc
    if not isinstance(result, dict):
        raise WakeDeliveryError("WAKE_INVALID_RESPONSE")
    top_level_code = result.get("status_code", result.get("code"))
    nested = result.get("data")
    nested_code = nested.get("code") if isinstance(nested, dict) else None
    if top_level_code not in {0, "0"} or nested_code not in {None, 0, "0"}:
        raise WakeDeliveryError("WAKE_BUSINESS_REJECTED")


def _payload(delivery: AgentWakeDelivery, channel: AgentWakeChannel) -> dict[str, str]:
    if channel.channel_type == "feishu_notification_webhook":
        return {
            "schema": "agentpost.feishu.notification.v1",
            "event_id": str(delivery.id),
            "task_id": str(delivery.task_id),
            "assignment_id": str(delivery.assignment_id),
            "run_id": str(delivery.run_id),
            "agent_id": str(delivery.agent_id),
            "action": "task_assignment_notification",
        }
    return {
        "schema": "agentpost.feishu_aily.wake.v1",
        "event_id": str(delivery.id),
        "task_id": str(delivery.task_id),
        "assignment_id": str(delivery.assignment_id),
        "run_id": str(delivery.run_id),
        "action": "claim_agentpost_run",
    }


def _record_channel_success(
    channel: AgentWakeChannel,
    connector: ConnectorInstance | None,
    *,
    tested: bool = False,
) -> None:
    now = utc_now()
    channel.status = "active"
    if tested:
        channel.last_tested_at = now
    channel.last_success_at = now
    channel.last_error_code = None
    channel.updated_at = now
    if channel.channel_type == "feishu_aily_webhook" and connector is not None:
        connector.task_listener_status = "listening"
        connector.task_listener_session_id = "feishu-aily-webhook"
        connector.task_listener_last_heartbeat_at = now
        connector.wake_capability = "automatic"


def test_wake_channel(
    session: Session,
    settings: Settings,
    *,
    user: HumanUser,
    agent_id: UUID,
    sender: WakeSender = send_webhook,
) -> None:
    _, connector = _owned_agent_connector(session, user=user, agent_id=agent_id)
    channel = session.scalar(
        select(AgentWakeChannel).where(
            AgentWakeChannel.agent_id == agent_id,
            AgentWakeChannel.status != "disabled",
        )
    )
    if channel is None:
        raise WakeChannelNotFoundError
    endpoint = decrypt_application_secret(
        channel.encrypted_endpoint, settings.human_mfa_encryption_key
    )
    _, hostname = _endpoint_parts(endpoint)
    try:
        _assert_allowed_host(settings, hostname)
    except WakeChannelInvalidEndpointError as exc:
        raise WakeDeliveryError("WAKE_ENDPOINT_NOT_ALLOWED") from exc
    token = decrypt_application_secret(
        channel.encrypted_bearer_token, settings.human_mfa_encryption_key
    )
    test_id = UUID(int=0)
    try:
        sender(
            endpoint,
            token,
            {
                "schema": (
                    "agentpost.feishu_aily.wake.v1"
                    if channel.channel_type == "feishu_aily_webhook"
                    else "agentpost.feishu.notification.v1"
                ),
                "event_id": str(test_id),
                "task_id": str(test_id),
                "assignment_id": str(test_id),
                "run_id": str(test_id),
                "action": (
                    "verify_agentpost_wake_channel"
                    if channel.channel_type == "feishu_aily_webhook"
                    else "verify_feishu_notification_channel"
                ),
            },
        )
    except WakeDeliveryError as exc:
        channel.status = "error"
        channel.last_tested_at = utc_now()
        channel.last_error_code = exc.code
        channel.updated_at = utc_now()
        if channel.channel_type == "feishu_aily_webhook" and connector is not None:
            connector.wake_capability = "automatic"
            connector.task_listener_status = "error"
            connector.task_listener_last_heartbeat_at = utc_now()
        session.commit()
        raise
    _record_channel_success(channel, connector, tested=True)
    session.commit()


def dispatch_pending_wakes(
    session: Session,
    settings: Settings,
    *,
    sender: WakeSender = send_webhook,
    limit: int = 20,
) -> int:
    now = utc_now()
    rows = list(
        session.scalars(
            select(AgentWakeDelivery)
            .where(
                AgentWakeDelivery.status == "pending",
                AgentWakeDelivery.available_at <= now,
            )
            .order_by(AgentWakeDelivery.created_at, AgentWakeDelivery.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    delivered = 0
    for delivery in rows:
        channel = session.get(AgentWakeChannel, delivery.channel_id)
        connector = (
            session.get(ConnectorInstance, channel.connector_instance_id)
            if channel is not None and channel.connector_instance_id is not None
            else None
        )
        if (
            channel is None
            or channel.status == "disabled"
            or (channel.channel_type == "feishu_aily_webhook" and connector is None)
        ):
            delivery.status = "cancelled"
            continue
        run = session.get(AgentRun, delivery.run_id)
        if run is None or run.status != "queued":
            delivery.status = "cancelled"
            continue
        delivery.status = "sending"
        delivery.attempts += 1
        delivery.last_attempt_at = now
        endpoint = decrypt_application_secret(
            channel.encrypted_endpoint, settings.human_mfa_encryption_key
        )
        _, hostname = _endpoint_parts(endpoint)
        try:
            _assert_allowed_host(settings, hostname)
        except WakeChannelInvalidEndpointError:
            delivery.status = "failed"
            delivery.last_error_code = "WAKE_ENDPOINT_NOT_ALLOWED"
            delivery.updated_at = utc_now()
            channel.status = "error"
            channel.last_error_code = "WAKE_ENDPOINT_NOT_ALLOWED"
            continue
        token = decrypt_application_secret(
            channel.encrypted_bearer_token, settings.human_mfa_encryption_key
        )
        try:
            sender(endpoint, token, _payload(delivery, channel))
        except WakeDeliveryError as exc:
            delivery.last_error_code = exc.code
            if delivery.attempts >= settings.wake_dispatch_max_attempts:
                delivery.status = "failed"
                channel.status = "error"
                channel.last_error_code = exc.code
            else:
                delivery.status = "pending"
                delivery.available_at = now + timedelta(seconds=2**delivery.attempts * 5)
            delivery.updated_at = utc_now()
            continue
        delivery.status = "delivered"
        delivery.delivered_at = utc_now()
        delivery.last_error_code = None
        delivery.updated_at = utc_now()
        _record_channel_success(channel, connector)
        delivered += 1
    session.commit()
    return delivered
