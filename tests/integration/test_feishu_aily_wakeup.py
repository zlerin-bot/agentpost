from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from agentpost.config import Settings
from agentpost.control.models import AgentOwnership, HumanUser
from agentpost.db import Database
from agentpost.identity.models import Agent, utc_now
from agentpost.onboarding.models import AgentConnectorBinding, ConnectorInstance
from agentpost.tasks.models import AgentRun, Task, TaskAssignment
from agentpost.tasks.service import _queue_collaboration_assignment
from agentpost.wakeup.models import AgentWakeChannel, AgentWakeDelivery
from agentpost.wakeup.schemas import FeishuAilyWakeChannelCreate
from agentpost.wakeup.service import (
    WakeChannelInvalidEndpointError,
    WakeDeliveryError,
    configure_feishu_notification_channel,
    configure_wake_channel,
    disable_wake_channel,
    dispatch_pending_wakes,
    enqueue_run_wake,
    get_wake_channel,
)
from agentpost.wakeup.service import (
    test_wake_channel as verify_wake_channel,
)


def _seed_feishu_agent(database: Database) -> tuple[HumanUser, Agent, ConnectorInstance]:
    with database.session_factory() as session:
        user = HumanUser(
            email=f"aily-{uuid4()}@example.com",
            username=f"aily-{uuid4().hex[:8]}",
            display_name="Aily Owner",
        )
        agent = Agent(
            address=f"aily-{uuid4().hex[:8]}@agents.local",
            display_name="mars的小跟班",
            domain="agents.local",
            capabilities=["task-collaboration"],
        )
        session.add_all([user, agent])
        session.flush()
        connector = ConnectorInstance(
            connector_id=f"con_{uuid4().hex}",
            agent_id=agent.id,
            human_user_id=user.id,
            connector_type="feishu_aily",
            display_name="飞书 aily 智能体",
            status="active",
        )
        session.add_all(
            [
                AgentOwnership(agent_id=agent.id, human_user_id=user.id),
                connector,
            ]
        )
        session.flush()
        session.add(
            AgentConnectorBinding(
                agent_id=agent.id,
                connector_instance_id=connector.id,
            )
        )
        session.commit()
        session.refresh(user)
        session.refresh(agent)
        session.refresh(connector)
        session.expunge_all()
        return user, agent, connector


def _seed_codex_agent(database: Database) -> tuple[HumanUser, Agent, ConnectorInstance]:
    with database.session_factory() as session:
        user = HumanUser(
            email=f"notify-{uuid4()}@example.com",
            username=f"notify-{uuid4().hex[:8]}",
            display_name="Notification Owner",
        )
        agent = Agent(
            address=f"codex-{uuid4().hex[:8]}@agents.local",
            display_name="Owner Codex",
            domain="agents.local",
            capabilities=["task-collaboration"],
        )
        session.add_all([user, agent])
        session.flush()
        connector = ConnectorInstance(
            connector_id=f"con_{uuid4().hex}",
            agent_id=agent.id,
            human_user_id=user.id,
            connector_type="codex",
            display_name="Codex",
            status="active",
            task_listener_status=None,
            wake_capability="manual",
        )
        session.add_all([AgentOwnership(agent_id=agent.id, human_user_id=user.id), connector])
        session.flush()
        session.add(AgentConnectorBinding(agent_id=agent.id, connector_instance_id=connector.id))
        session.commit()
        session.expunge_all()
        return user, agent, connector


def _seed_queued_run(
    database: Database, *, user: HumanUser, agent: Agent
) -> tuple[Task, TaskAssignment, AgentRun]:
    with database.session_factory() as session:
        task = Task(
            owner_human_user_id=user.id,
            coordinator_agent_id=agent.id,
            title="验证飞书自动接任务",
            goal="验证自动唤醒",
            expected_output="返回测试结果",
        )
        session.add(task)
        session.flush()
        assignment = TaskAssignment(
            task_id=task.id,
            responsible_human_user_id=user.id,
            assignee_agent_id=agent.id,
            created_by_human_user_id=user.id,
            instruction="读取任务并反馈",
            expected_output=task.expected_output,
        )
        session.add(assignment)
        session.flush()
        run = AgentRun(assignment_id=assignment.id, agent_id=agent.id)
        session.add(run)
        session.commit()
        session.refresh(task)
        session.refresh(assignment)
        session.refresh(run)
        session.expunge_all()
        return task, assignment, run


def _payload(url: str = "https://aily.example.com/hooks/agentpost") -> FeishuAilyWakeChannelCreate:
    return FeishuAilyWakeChannelCreate(
        webhook_url=url,
        bearer_token="aily-secret-token",
    )


def test_wake_channel_encrypts_secrets_and_hides_them_from_status(
    database: Database, settings: Settings
) -> None:
    user, agent, _ = _seed_feishu_agent(database)
    with database.session_factory() as session:
        status = configure_wake_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=_payload(),
        )
        channel = session.scalar(select(AgentWakeChannel))
        assert channel is not None
        assert "aily.example.com" not in channel.encrypted_endpoint
        assert "aily-secret-token" not in channel.encrypted_bearer_token
        assert status.endpoint_host == "aily.example.com"
        assert "webhook" not in status.model_dump()
        assert "token" not in status.model_dump()
        assert (
            get_wake_channel(
                session,
                settings,
                user=session.get(HumanUser, user.id),
                agent_id=agent.id,
            )
            == status
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://aily.example.com/hook",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.8/hook",
        "https://[::1]/hook",
        "https://aily.example.com:8443/hook",
        "https://例子.测试/hook",
        "https://user:pass@aily.example.com/hook",
    ],
)
def test_wake_channel_rejects_non_public_or_credentialed_endpoints(
    database: Database, settings: Settings, url: str
) -> None:
    user, agent, _ = _seed_feishu_agent(database)
    with database.session_factory() as session:
        with pytest.raises(WakeChannelInvalidEndpointError):
            configure_wake_channel(
                session,
                settings,
                user=session.get(HumanUser, user.id),
                agent_id=agent.id,
                payload=_payload(url),
            )


def test_wake_channel_honors_the_server_host_allowlist(
    database: Database, settings: Settings
) -> None:
    user, agent, _ = _seed_feishu_agent(database)
    restricted = settings.model_copy(
        update={"feishu_aily_wake_allowed_hosts": "hooks.aily.example"}
    )
    with database.session_factory() as session:
        with pytest.raises(WakeChannelInvalidEndpointError):
            configure_wake_channel(
                session,
                restricted,
                user=session.get(HumanUser, user.id),
                agent_id=agent.id,
                payload=_payload(),
            )


def test_channel_test_and_dispatch_expose_only_ids_and_mark_listener_ready(
    database: Database, settings: Settings
) -> None:
    user, agent, connector = _seed_feishu_agent(database)
    task, assignment, run = _seed_queued_run(database, user=user, agent=agent)
    sent: list[tuple[str, str, dict[str, str]]] = []

    def sender(endpoint: str, token: str, payload: dict[str, str]) -> None:
        sent.append((endpoint, token, payload))

    with database.session_factory() as session:
        configure_wake_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=_payload(),
        )
        verify_wake_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            sender=sender,
        )
        assert sent[-1][2]["action"] == "verify_agentpost_wake_channel"
        assert dispatch_pending_wakes(session, settings, sender=sender) == 1
        delivery = session.scalar(select(AgentWakeDelivery))
        refreshed_connector = session.get(ConnectorInstance, connector.id)
        assert delivery is not None and delivery.status == "delivered"
        assert refreshed_connector is not None
        assert refreshed_connector.task_listener_status == "listening"
        assert refreshed_connector.wake_capability == "automatic"

    endpoint, token, payload = sent[-1]
    assert endpoint == "https://aily.example.com/hooks/agentpost"
    assert token == "aily-secret-token"
    assert payload == {
        "_auth_scheme": "bearer",
        "schema": "agentpost.feishu_aily.wake.v1",
        "event_id": str(delivery.id),
        "task_id": str(task.id),
        "assignment_id": str(assignment.id),
        "run_id": str(run.id),
        "action": "claim_agentpost_run",
    }
    assert "验证飞书" not in str(payload)


def test_human_feishu_notification_is_independent_from_agent_execution(
    database: Database, settings: Settings
) -> None:
    user, agent, connector = _seed_codex_agent(database)
    task, assignment, run = _seed_queued_run(database, user=user, agent=agent)
    sent: list[tuple[str, str, dict[str, str]]] = []

    def sender(endpoint: str, token: str, payload: dict[str, str]) -> None:
        sent.append((endpoint, token, payload))

    with database.session_factory() as session:
        status = configure_feishu_notification_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=_payload("https://aily.feishu.cn/hooks/notify"),
        )
        channel = session.scalar(select(AgentWakeChannel))
        assert status.channel_type == "feishu_notification_webhook"
        assert channel is not None and channel.connector_instance_id is None
        verify_wake_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            sender=sender,
        )
        assert sent[-1][2]["action"] == "verify_feishu_notification_channel"
        assert session.scalar(select(AgentWakeDelivery)) is None  # no historical flood on save
        enqueue_run_wake(
            session,
            agent_id=agent.id,
            task_id=task.id,
            assignment_id=assignment.id,
            run_id=run.id,
        )
        session.commit()
        assert dispatch_pending_wakes(session, settings, sender=sender) == 0
        with pytest.raises(WakeDeliveryError, match="WAKE_RATE_LIMITED"):
            verify_wake_channel(
                session,
                settings,
                user=session.get(HumanUser, user.id),
                agent_id=agent.id,
                sender=sender,
            )
        channel.last_dispatch_at = utc_now() - timedelta(seconds=61)
        queued = session.scalar(select(AgentWakeDelivery))
        queued.available_at = utc_now() - timedelta(seconds=1)
        session.commit()
        assert dispatch_pending_wakes(session, settings, sender=sender) == 1
        refreshed_connector = session.get(ConnectorInstance, connector.id)
        assert refreshed_connector is not None
        assert refreshed_connector.task_listener_status is None
        assert refreshed_connector.wake_capability == "manual"
        delivery = session.scalar(select(AgentWakeDelivery))
        assert delivery is not None
        delivery_id = delivery.id

    assert sent[-1][2] == {
        "_auth_scheme": "bearer",
        "schema": "agentpost.feishu.notification.v1",
        "event_id": str(delivery_id),
        "task_id": str(task.id),
        "assignment_id": str(assignment.id),
        "run_id": str(run.id),
        "agent_id": str(agent.id),
        "action": "task_assignment_notification",
    }


def test_task_assignment_creates_wake_outbox_in_the_same_transaction(
    database: Database, settings: Settings
) -> None:
    user, agent, _ = _seed_feishu_agent(database)
    with database.session_factory() as session:
        configure_wake_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=_payload(),
        )
        task = Task(
            owner_human_user_id=user.id,
            coordinator_agent_id=agent.id,
            title="同事务测试",
            goal="创建工单时写入唤醒记录",
            expected_output="一条待发记录",
        )
        session.add(task)
        session.flush()
        assignment = _queue_collaboration_assignment(
            session,
            task=task,
            human_id=user.id,
            agent_id=agent.id,
            created_by_human_id=user.id,
            assignment_kind="human_directed",
        )
        delivery = session.scalar(
            select(AgentWakeDelivery).where(AgentWakeDelivery.assignment_id == assignment.id)
        )
        run = session.scalar(select(AgentRun).where(AgentRun.assignment_id == assignment.id))
        assert delivery is not None
        assert run is not None and delivery.run_id == run.id
        task_id = task.id
        assignment_id = assignment.id
        delivery_id = delivery.id
        session.rollback()

    with database.session_factory() as session:
        assert session.get(Task, task_id) is None
        assert session.get(TaskAssignment, assignment_id) is None
        assert session.get(AgentWakeDelivery, delivery_id) is None


def test_failed_delivery_retries_then_stops_and_disable_cancels_pending(
    database: Database, settings: Settings
) -> None:
    user, agent, connector = _seed_feishu_agent(database)
    task, assignment, first_run = _seed_queued_run(database, user=user, agent=agent)
    limited_settings = settings.model_copy(update={"wake_dispatch_max_attempts": 1})

    def fail_sender(_endpoint: str, _token: str, _payload: dict[str, str]) -> None:
        raise WakeDeliveryError("WAKE_HTTP_401")

    with database.session_factory() as session:
        configure_wake_channel(
            session,
            limited_settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=_payload(),
        )
        assert dispatch_pending_wakes(session, limited_settings, sender=fail_sender) == 0
        delivery = session.scalar(
            select(AgentWakeDelivery).where(AgentWakeDelivery.run_id == first_run.id)
        )
        channel = session.scalar(select(AgentWakeChannel))
        assert delivery is not None and delivery.status == "failed"
        assert delivery.attempts == 1
        assert channel is not None and channel.status == "error"

        second_run = AgentRun(assignment_id=assignment.id, agent_id=agent.id, attempt=2)
        session.add(second_run)
        session.flush()
        enqueue_run_wake(
            session,
            agent_id=agent.id,
            task_id=task.id,
            assignment_id=assignment.id,
            run_id=second_run.id,
        )
        session.commit()
        disable_wake_channel(
            session,
            limited_settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
        )
        pending = session.scalar(
            select(AgentWakeDelivery).where(AgentWakeDelivery.run_id == second_run.id)
        )
        refreshed_connector = session.get(ConnectorInstance, connector.id)
        assert pending is not None and pending.status == "cancelled"
        assert refreshed_connector is not None
        assert refreshed_connector.task_listener_status == "stopped"
        assert refreshed_connector.wake_capability == "manual"


def test_notification_timeout_is_not_retried_and_test_ids_are_unique(database, settings):
    user, agent, _ = _seed_codex_agent(database)
    task, assignment, run = _seed_queued_run(database, user=user, agent=agent)
    sent = []
    with database.session_factory() as session:
        configure_feishu_notification_channel(
            session,
            settings,
            user=session.get(HumanUser, user.id),
            agent_id=agent.id,
            payload=FeishuAilyWakeChannelCreate(
                webhook_url="https://aily.example.com/hook",
                bearer_token="signing-secret",
                auth_scheme="hmac_sha256",
            ),
        )
        channel = session.scalar(select(AgentWakeChannel))
        for _ in range(2):
            channel.last_dispatch_at = utc_now() - timedelta(seconds=61)
            session.commit()
            verify_wake_channel(
                session,
                settings,
                user=session.get(HumanUser, user.id),
                agent_id=agent.id,
                sender=lambda _u, _t, data: sent.append(data),
            )
        assert sent[0]["event_id"] != sent[1]["event_id"]
        assert sent[0]["_auth_scheme"] == "hmac_sha256"
        enqueue_run_wake(
            session, agent_id=agent.id, task_id=task.id, assignment_id=assignment.id, run_id=run.id
        )
        channel.last_dispatch_at = utc_now() - timedelta(seconds=61)
        session.commit()

        def fail(_u, _t, data):
            sent.append(data)
            raise WakeDeliveryError("WAKE_TRANSPORT_ERROR")

        assert dispatch_pending_wakes(session, settings, sender=fail) == 0
        delivery = session.scalar(select(AgentWakeDelivery))
        assert delivery.status == "failed"
        assert delivery.attempts == 1
        assert channel.status == "error"
        assert dispatch_pending_wakes(session, settings, sender=fail) == 0
        assert len(sent) == 3
        assert session.get(AgentRun, run.id).status == "queued"
