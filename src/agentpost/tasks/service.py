from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agentpost.accounts.mailer import EmailDeliveryError, deliver_task_membership_notification
from agentpost.attachments.models import Attachment
from agentpost.attachments.service import attachment_metadata, bind_attachments
from agentpost.config import Settings
from agentpost.control.human_security import add_human_action_audit
from agentpost.control.models import AgentOwnership, HumanUser
from agentpost.identity.models import Agent, utc_now
from agentpost.messaging.models import Delivery, Message
from agentpost.onboarding.models import AgentConnectorBinding, ConnectorInstance
from agentpost.tasks.models import (
    AgentRun,
    Friendship,
    Task,
    TaskActivity,
    TaskActivityRelation,
    TaskAgentParticipant,
    TaskAssignment,
    TaskMembership,
)
from agentpost.tasks.schemas import (
    AgentChoice,
    AgentCollaborationUpdate,
    AgentRunClaim,
    AgentRunPending,
    AgentRunPendingList,
    AgentRunResult,
    AgentRunUpdate,
    AgentSummary,
    AgentTaskCandidate,
    AgentTaskCreate,
    AgentTaskMessageCreate,
    AgentTaskMessageResponse,
    AgentTaskResolution,
    FriendResponse,
    TaskAcceptanceDecision,
    TaskActivityReplyRelationCreate,
    TaskActivityResponse,
    TaskAssignmentBatchCreate,
    TaskAssignmentCreate,
    TaskAssignmentResponse,
    TaskCreate,
    TaskDetail,
    TaskFinalSubmission,
    TaskMember,
    TaskRunHumanResponse,
    TaskRunStateCounts,
    TaskStateAxes,
    TaskSummary,
)

RUN_LEASE_SECONDS = 90


class TaskNotFoundError(Exception):
    pass


class TaskOwnerRequiredError(Exception):
    pass


class TaskStateConflictError(Exception):
    pass


class TaskAgentSelectionError(Exception):
    pass


class FriendshipNotFoundError(Exception):
    pass


class FriendshipConflictError(Exception):
    pass


class AgentRunNotFoundError(Exception):
    pass


class AgentRunLeaseError(Exception):
    pass


class TaskMessageIdempotencyConflictError(Exception):
    pass


class TaskHumanResponseForbiddenError(Exception):
    pass


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _pair(first: UUID, second: UUID) -> tuple[UUID, UUID]:
    return tuple(sorted((first, second), key=str))  # type: ignore[return-value]


def _friendship_for(session: Session, first: UUID, second: UUID, *, lock: bool = False):
    human_a_id, human_b_id = _pair(first, second)
    statement = select(Friendship).where(
        Friendship.human_a_id == human_a_id,
        Friendship.human_b_id == human_b_id,
    )
    if lock:
        statement = statement.with_for_update()
    return session.scalar(statement)


def _human_agent(session: Session, human_id: UUID, agent_id: UUID) -> Agent | None:
    return session.scalar(
        select(Agent)
        .join(AgentOwnership, AgentOwnership.agent_id == Agent.id)
        .where(
            Agent.id == agent_id,
            AgentOwnership.human_user_id == human_id,
            Agent.status == "active",
        )
    )


def _validate_agent_choice(session: Session, *, human_id: UUID, choice: AgentChoice) -> list[Agent]:
    rows = list(
        session.scalars(
            select(Agent)
            .join(AgentOwnership, AgentOwnership.agent_id == Agent.id)
            .where(
                Agent.id.in_(choice.agent_ids),
                AgentOwnership.human_user_id == human_id,
                Agent.status == "active",
            )
        )
    )
    if {agent.id for agent in rows} != set(choice.agent_ids):
        raise TaskAgentSelectionError
    return rows


def _agent_summary(agent: Agent, *, role: str | None = None) -> AgentSummary:
    return AgentSummary(
        agent_id=agent.id,
        display_name=agent.display_name,
        address=agent.address,
        capabilities=[item for item in agent.capabilities if isinstance(item, str)],
        role=role,  # type: ignore[arg-type]
    )


def list_friend_suggestions(
    session: Session, *, user: HumanUser, query: str | None = None, limit: int = 20
) -> list[FriendResponse]:
    normalized = query.strip().casefold() if query else ""
    exact_human_ids: set[UUID] = set()
    if normalized:
        try:
            exact_human_ids.add(UUID(normalized))
        except ValueError:
            pass
        exact_human_ids.update(
            session.scalars(
                select(HumanUser.id).where(
                    HumanUser.status == "active",
                    func.lower(HumanUser.username) == normalized,
                )
            )
        )
        try:
            exact_agent_id = UUID(normalized)
        except ValueError:
            exact_agent_id = None
        agent_conditions = [
            func.lower(Agent.address) == normalized,
            func.lower(Agent.handle) == normalized,
        ]
        if exact_agent_id is not None:
            agent_conditions.append(Agent.id == exact_agent_id)
        exact_human_ids.update(
            session.scalars(
                select(AgentOwnership.human_user_id)
                .join(Agent, Agent.id == AgentOwnership.agent_id)
                .where(Agent.status == "active", or_(*agent_conditions))
            )
        )
        exact_human_ids.discard(user.id)
        exact_humans = list(
            session.scalars(
                select(HumanUser).where(
                    HumanUser.id.in_(exact_human_ids), HumanUser.status == "active"
                )
            )
        )
        exact_results = []
        for human in exact_humans:
            friendship = _friendship_for(session, user.id, human.id)
            if friendship is not None and friendship.status in {"pending", "accepted"}:
                continue
            exact_results.append(
                FriendResponse(
                    human_user_id=human.id,
                    username=human.username,
                    display_name=human.display_name,
                    relation_status="suggested",
                )
            )
        if exact_results:
            return exact_results[:limit]
    owned_ids = set(
        session.scalars(
            select(AgentOwnership.agent_id).where(AgentOwnership.human_user_id == user.id)
        )
    )
    if not owned_ids:
        return []
    contacted: dict[UUID, datetime] = {}
    rows = session.execute(
        select(Delivery.recipient_agent_id, func.max(Message.created_at))
        .join(Message, Message.id == Delivery.message_id)
        .where(Message.sender_agent_id.in_(owned_ids))
        .group_by(Delivery.recipient_agent_id)
    ).all()
    rows += session.execute(
        select(Message.sender_agent_id, func.max(Message.created_at))
        .join(Delivery, Delivery.message_id == Message.id)
        .where(Delivery.recipient_agent_id.in_(owned_ids))
        .group_by(Message.sender_agent_id)
    ).all()
    for agent_id, contacted_at in rows:
        if agent_id in owned_ids or contacted_at is None:
            continue
        current = contacted.get(agent_id)
        if current is None or contacted_at > current:
            contacted[agent_id] = contacted_at
    if not contacted:
        return []
    candidates = session.execute(
        select(Agent, HumanUser)
        .join(AgentOwnership, AgentOwnership.agent_id == Agent.id)
        .join(HumanUser, HumanUser.id == AgentOwnership.human_user_id)
        .where(
            Agent.id.in_(contacted),
            Agent.status == "active",
            HumanUser.status == "active",
            HumanUser.id != user.id,
        )
    ).all()
    grouped: dict[UUID, tuple[HumanUser, datetime]] = {}
    for agent, human in candidates:
        if normalized and normalized not in f"{human.username} {human.display_name}".casefold():
            continue
        last_contact = contacted[agent.id]
        previous = grouped.get(human.id)
        if previous is None or last_contact > previous[1]:
            grouped[human.id] = (human, last_contact)
    result: list[FriendResponse] = []
    for human, last_contact in sorted(grouped.values(), key=lambda item: item[1], reverse=True):
        friendship = _friendship_for(session, user.id, human.id)
        if friendship is not None and friendship.status in {"pending", "accepted"}:
            continue
        result.append(
            FriendResponse(
                human_user_id=human.id,
                username=human.username,
                display_name=human.display_name,
                relation_status="suggested",
                last_contact_at=_as_utc(last_contact),
            )
        )
        if len(result) >= limit:
            break
    return result


def list_friends(
    session: Session, *, user: HumanUser, query: str | None = None, limit: int = 100
) -> list[FriendResponse]:
    friendships = list(
        session.scalars(
            select(Friendship)
            .where(
                or_(Friendship.human_a_id == user.id, Friendship.human_b_id == user.id),
                Friendship.status.in_(["pending", "accepted"]),
            )
            .order_by(Friendship.updated_at.desc())
            .limit(limit)
        )
    )
    other_ids = {
        friendship.human_b_id if friendship.human_a_id == user.id else friendship.human_a_id
        for friendship in friendships
    }
    humans = {
        human.id: human
        for human in session.scalars(select(HumanUser).where(HumanUser.id.in_(other_ids)))
    }
    normalized = query.strip().casefold() if query else ""
    response: list[FriendResponse] = []
    for friendship in friendships:
        other_id = (
            friendship.human_b_id if friendship.human_a_id == user.id else friendship.human_a_id
        )
        human = humans.get(other_id)
        if human is None:
            continue
        if friendship.status == "accepted":
            relation = "accepted"
        elif friendship.requested_by_human_id == user.id:
            relation = "pending_outgoing"
        else:
            relation = "pending_incoming"
        agents: list[AgentSummary] = []
        if friendship.status == "accepted" and human.default_agent_id:
            agent = _human_agent(session, human.id, human.default_agent_id)
            if agent is not None:
                agents.append(_agent_summary(agent))
        searchable = " ".join(
            [
                human.username,
                human.display_name,
                str(human.id),
                *[
                    f"{agent.display_name} {agent.address} {agent.agent_id} "
                    f"{' '.join(agent.capabilities)}"
                    for agent in agents
                ],
            ]
        ).casefold()
        if normalized and normalized not in searchable:
            continue
        response.append(
            FriendResponse(
                friendship_id=friendship.id,
                human_user_id=human.id,
                username=human.username,
                display_name=human.display_name,
                relation_status=relation,  # type: ignore[arg-type]
                agents=agents,
            )
        )
    return response


def request_friendship(
    session: Session,
    *,
    user: HumanUser,
    username: str,
    human_session_id: UUID | None,
    request_id: str | None,
) -> FriendResponse:
    target = session.scalar(
        select(HumanUser).where(
            HumanUser.username == username.strip().casefold(), HumanUser.status == "active"
        )
    )
    if target is None or target.id == user.id:
        raise FriendshipNotFoundError
    existing = _friendship_for(session, user.id, target.id, lock=True)
    now = utc_now()
    if existing is not None and existing.status in {"pending", "accepted"}:
        raise FriendshipConflictError
    human_a_id, human_b_id = _pair(user.id, target.id)
    friendship = existing or Friendship(
        human_a_id=human_a_id,
        human_b_id=human_b_id,
        requested_at=now,
    )
    friendship.requested_by_human_id = user.id
    friendship.status = "pending"
    friendship.requested_at = now
    friendship.responded_at = None
    friendship.updated_at = now
    session.add(friendship)
    session.flush()
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="friendship.requested",
        target_type="friendship",
        target_id=str(friendship.id),
        outcome="success",
        request_id=request_id,
        audit_metadata={"target_human_user_id": str(target.id)},
    )
    session.commit()
    return FriendResponse(
        friendship_id=friendship.id,
        human_user_id=target.id,
        username=target.username,
        display_name=target.display_name,
        relation_status="pending_outgoing",
    )


def decide_friendship(
    session: Session,
    *,
    user: HumanUser,
    friendship_id: UUID,
    accept: bool,
    human_session_id: UUID | None,
    request_id: str | None,
) -> FriendResponse:
    friendship = session.scalar(
        select(Friendship).where(Friendship.id == friendship_id).with_for_update()
    )
    if (
        friendship is None
        or friendship.status != "pending"
        or friendship.requested_by_human_id == user.id
        or user.id not in {friendship.human_a_id, friendship.human_b_id}
    ):
        raise FriendshipNotFoundError
    now = utc_now()
    friendship.status = "accepted" if accept else "declined"
    friendship.responded_at = now
    friendship.updated_at = now
    other_id = friendship.human_b_id if friendship.human_a_id == user.id else friendship.human_a_id
    other = session.get(HumanUser, other_id)
    if other is None:
        raise FriendshipNotFoundError
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="friendship.accepted" if accept else "friendship.declined",
        target_type="friendship",
        target_id=str(friendship.id),
        outcome="success",
        request_id=request_id,
        audit_metadata={"other_human_user_id": str(other.id)},
    )
    session.commit()
    return FriendResponse(
        friendship_id=friendship.id,
        human_user_id=other.id,
        username=other.username,
        display_name=other.display_name,
        relation_status="accepted" if accept else "pending_incoming",
    )


def remove_friendship(
    session: Session,
    *,
    user: HumanUser,
    friendship_id: UUID,
    human_session_id: UUID | None,
    request_id: str | None,
) -> None:
    friendship = session.scalar(
        select(Friendship).where(Friendship.id == friendship_id).with_for_update()
    )
    if (
        friendship is None
        or friendship.status != "accepted"
        or user.id not in {friendship.human_a_id, friendship.human_b_id}
    ):
        raise FriendshipNotFoundError
    friendship.status = "removed"
    friendship.updated_at = utc_now()
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="friendship.removed",
        target_type="friendship",
        target_id=str(friendship.id),
        outcome="success",
        request_id=request_id,
        audit_metadata={},
    )
    session.commit()


def _task_context(
    session: Session, *, task_id: UUID, user: HumanUser, lock: bool = False
) -> tuple[Task, TaskMembership]:
    statement = select(Task).where(Task.id == task_id)
    if lock:
        statement = statement.with_for_update()
    task = session.scalar(statement)
    membership = session.scalar(
        select(TaskMembership).where(
            TaskMembership.task_id == task_id,
            TaskMembership.human_user_id == user.id,
            TaskMembership.status.in_(["active", "invited"]),
        )
    )
    if task is None or membership is None:
        raise TaskNotFoundError
    return task, membership


def _require_owner(task: Task, membership: TaskMembership) -> None:
    if membership.role != "owner" or membership.status != "active":
        raise TaskOwnerRequiredError
    if task.owner_human_user_id != membership.human_user_id:
        raise TaskOwnerRequiredError


def _add_activity(
    session: Session,
    *,
    task_id: UUID,
    kind: str,
    actor_type: str,
    actor_human_id: UUID | None = None,
    actor_agent_id: UUID | None = None,
    target_human_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
    external: bool = False,
    idempotency_key: str | None = None,
    request_hash: str | None = None,
) -> TaskActivity:
    # Serialize publication for this Task until commit. A later transaction cannot
    # publish past an uncommitted activity. Timestamps remain original audit facts.
    session.execute(select(Task.id).where(Task.id == task_id).with_for_update())
    persisted = (
        session.scalar(
            select(func.max(TaskActivity.sequence)).where(TaskActivity.task_id == task_id)
        )
        or 0
    )
    pending = [
        item.sequence
        for item in session.new
        if isinstance(item, TaskActivity) and item.task_id == task_id
    ]
    activity = TaskActivity(
        sequence=max([persisted, *pending]) + 1,
        task_id=task_id,
        activity_type=kind,
        actor_type=actor_type,
        actor_human_user_id=actor_human_id,
        actor_agent_id=actor_agent_id,
        target_human_user_id=target_human_id,
        activity_metadata=metadata or {},
        security_label="external_agent_content" if external else "platform_event",
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    session.add(activity)
    return activity


def _queue_collaboration_assignment(
    session: Session,
    *,
    task: Task,
    human_id: UUID,
    agent_id: UUID,
    created_by_human_id: UUID,
    assignment_kind: str = "participant_start",
    trigger_activity_id: UUID | None = None,
    source_message_id: str | None = None,
    priority: str = "normal",
    instruction: str | None = None,
    expected_output: str | None = None,
    due_at: datetime | None = None,
) -> TaskAssignment:
    join_activity: TaskActivity | None = None
    if assignment_kind == "participant_start" and trigger_activity_id is None:
        join_activity = _add_activity(
            session,
            task_id=task.id,
            kind="agent_joined_collaboration",
            actor_type="platform",
            target_human_id=human_id,
            metadata={"agent_id": str(agent_id)},
        )
        session.flush()
        trigger_activity_id = join_activity.id
    assignment = TaskAssignment(
        task_id=task.id,
        responsible_human_user_id=human_id,
        assignee_agent_id=agent_id,
        created_by_human_user_id=created_by_human_id,
        assignment_kind=assignment_kind,
        trigger_activity_id=trigger_activity_id,
        source_message_id=source_message_id,
        priority=priority,
        instruction=instruction
        or (
            "你已加入这个任务的协同。请结合完整任务目标和其他参与者的进展，"
            "主动贡献、报告阻塞或明确说明暂不需要行动。"
        ),
        expected_output=expected_output or task.expected_output,
        due_at=due_at if due_at is not None else task.due_at,
        status="queued",
    )
    session.add(assignment)
    session.flush()
    session.add(AgentRun(assignment_id=assignment.id, agent_id=agent_id))
    if join_activity is not None:
        join_activity.activity_metadata = {
            **join_activity.activity_metadata,
            "assignment_id": str(assignment.id),
        }
    return assignment


def _run_wake_stage(run: AgentRun) -> str:
    if run.status in {"completed", "partial", "failed", "cancelled", "interrupted"}:
        return "finished"
    if run.status in {"starting", "running", "waiting_human"}:
        return "running"
    if run.woken_at is not None:
        return "woken"
    if run.session_mapped_at is not None:
        return "mapped"
    if run.claimed_at is not None or run.status == "leased":
        return "claimed"
    return "queued"


def _task_state_axes(
    task: Task,
    assignments: list[TaskAssignmentResponse],
) -> TaskStateAxes:
    effective_assignments = [
        item
        for item in assignments
        if item.assignment_kind not in {"task_message", "result_sync"}
        and item.cancellation_reason != "legacy_pre_0_1_44_backlog"
    ]
    run_counts = {"queued": 0, "active": 0, "waiting_human": 0, "terminal": 0}
    for assignment in effective_assignments:
        status = assignment.run_status or assignment.status
        if status == "queued":
            run_counts["queued"] += 1
        elif status in {"leased", "starting", "running"}:
            run_counts["active"] += 1
        elif status == "waiting_human":
            run_counts["waiting_human"] += 1
        else:
            run_counts["terminal"] += 1

    result_states = {item.result_status for item in effective_assignments if item.result_status}
    if not result_states:
        result_status = "none"
    elif len([item for item in effective_assignments if item.result_status]) != len(
        effective_assignments
    ):
        result_status = "mixed"
    elif len(result_states) == 1:
        result_status = next(iter(result_states))
    else:
        result_status = "mixed"

    if task.accepted_at is not None:
        submission_status = "accepted"
        acceptance_status = "accepted"
    elif task.status == "awaiting_acceptance":
        submission_status = "awaiting_acceptance"
        acceptance_status = "pending"
    elif task.status in {"cancelled", "archived"}:
        submission_status = "cancelled"
        acceptance_status = "cancelled"
    elif task.revision > 1 and task.submitted_at is None:
        submission_status = "changes_requested"
        acceptance_status = "changes_requested"
    else:
        submission_status = "not_submitted"
        acceptance_status = "not_ready"

    return TaskStateAxes(
        task_status=task.status,
        run_counts=TaskRunStateCounts(**run_counts),
        agent_result_status=result_status,  # type: ignore[arg-type]
        submission_status=submission_status,  # type: ignore[arg-type]
        human_acceptance_status=acceptance_status,  # type: ignore[arg-type]
        submitted_at=_as_utc(task.submitted_at),
        accepted_at=_as_utc(task.accepted_at),
    )


def _task_detail(
    session: Session,
    *,
    task: Task,
    viewer_membership: TaskMembership,
    activity_limit: int = 200,
    activity_ids: list[UUID] | None = None,
    include_reply_parents: bool = True,
    include_assignments: bool = True,
) -> TaskDetail:
    membership_rows = session.execute(
        select(TaskMembership, HumanUser)
        .join(HumanUser, HumanUser.id == TaskMembership.human_user_id)
        .where(
            TaskMembership.task_id == task.id,
            TaskMembership.status.in_(["active", "invited"]),
        )
        .order_by(TaskMembership.role, TaskMembership.invited_at)
    ).all()
    human_ids = {human.id for _, human in membership_rows}
    humans = {human.id: human for _, human in membership_rows}
    agent_rows = session.execute(
        select(TaskAgentParticipant, Agent)
        .join(Agent, Agent.id == TaskAgentParticipant.agent_id)
        .where(TaskAgentParticipant.task_id == task.id, TaskAgentParticipant.active.is_(True))
    ).all()
    agents = {agent.id: agent for _, agent in agent_rows}
    human_id_by_agent = {
        participant.agent_id: participant.human_user_id for participant, _ in agent_rows
    }
    agents_by_human: dict[UUID, list[AgentSummary]] = {human_id: [] for human_id in human_ids}
    for participant, agent in agent_rows:
        agents_by_human.setdefault(participant.human_user_id, []).append(
            _agent_summary(agent, role=participant.role)
        )
    members = [
        TaskMember(
            human_user_id=human.id,
            username=human.username,
            display_name=human.display_name,
            role=membership.role,  # type: ignore[arg-type]
            status=membership.status,  # type: ignore[arg-type]
            primary_agent_id=membership.primary_agent_id,
            agent_selection_source=membership.agent_selection_source,  # type: ignore[arg-type]
            email_notification_status=membership.email_notification_status,  # type: ignore[arg-type]
            agents=agents_by_human.get(human.id, []),
            invited_at=_as_utc(membership.invited_at),
            joined_at=_as_utc(membership.joined_at),
        )
        for membership, human in membership_rows
    ]
    assignment_rows = list(
        session.scalars(
            select(TaskAssignment)
            .where(TaskAssignment.task_id == task.id)
            .where(include_assignments)
            .order_by(TaskAssignment.created_at.desc())
        )
    )
    historical_human_ids = {
        human_id
        for item in assignment_rows
        for human_id in (item.responsible_human_user_id, item.created_by_human_user_id)
    } - humans.keys()
    if historical_human_ids:
        humans.update(
            {
                human.id: human
                for human in session.scalars(
                    select(HumanUser).where(HumanUser.id.in_(historical_human_ids))
                )
            }
        )
    missing_assignment_agent_ids = {
        item.assignee_agent_id for item in assignment_rows if item.assignee_agent_id not in agents
    }
    if missing_assignment_agent_ids:
        agents.update(
            {
                agent.id: agent
                for agent in session.scalars(
                    select(Agent).where(Agent.id.in_(missing_assignment_agent_ids))
                )
            }
        )
    latest_run: dict[UUID, AgentRun] = {}
    if assignment_rows:
        for run in session.scalars(
            select(AgentRun)
            .where(AgentRun.assignment_id.in_([item.id for item in assignment_rows]))
            .order_by(AgentRun.attempt.desc())
        ):
            latest_run.setdefault(run.assignment_id, run)
    source_activity_ids = {
        item.trigger_activity_id for item in assignment_rows if item.trigger_activity_id is not None
    }
    source_activities = {
        item.id: item
        for item in session.scalars(
            select(TaskActivity).where(TaskActivity.id.in_(source_activity_ids))
        )
    }
    source_agent_ids = {
        item.actor_agent_id
        for item in source_activities.values()
        if item.actor_agent_id is not None
    }
    source_agents = {
        agent.id: agent
        for agent in session.scalars(select(Agent).where(Agent.id.in_(source_agent_ids)))
    }
    assignments = [
        TaskAssignmentResponse(
            assignment_id=item.id,
            responsible_human_user_id=item.responsible_human_user_id,
            responsible_human_display_name=humans[item.responsible_human_user_id].display_name,
            created_by_human_user_id=item.created_by_human_user_id,
            created_by_human_display_name=humans[item.created_by_human_user_id].display_name,
            assignee_agent_id=item.assignee_agent_id,
            assignee_agent_display_name=agents[item.assignee_agent_id].display_name,
            source_kind=(
                source_activities[item.trigger_activity_id].activity_type
                if item.trigger_activity_id in source_activities
                else None
            ),
            source_actor_type=(
                source_activities[item.trigger_activity_id].actor_type
                if item.trigger_activity_id in source_activities
                else None
            ),
            source_actor_human_display_name=(
                humans[source_activities[item.trigger_activity_id].actor_human_user_id].display_name
                if item.trigger_activity_id in source_activities
                and source_activities[item.trigger_activity_id].actor_human_user_id in humans
                else (
                    humans[
                        human_id_by_agent[
                            source_activities[item.trigger_activity_id].actor_agent_id
                        ]
                    ].display_name
                    if item.trigger_activity_id in source_activities
                    and source_activities[item.trigger_activity_id].actor_agent_id
                    in human_id_by_agent
                    and human_id_by_agent[
                        source_activities[item.trigger_activity_id].actor_agent_id
                    ]
                    in humans
                    else None
                )
            ),
            source_actor_agent_display_name=(
                source_agents[
                    source_activities[item.trigger_activity_id].actor_agent_id
                ].display_name
                if item.trigger_activity_id in source_activities
                and source_activities[item.trigger_activity_id].actor_agent_id in source_agents
                else None
            ),
            source_publication_origin=(
                source_activities[item.trigger_activity_id].activity_metadata.get(
                    "publication_origin"
                )
                if item.trigger_activity_id in source_activities
                and source_activities[item.trigger_activity_id].activity_metadata.get(
                    "publication_origin"
                )
                in {"human_delegated", "agent_autonomous"}
                else None
            ),
            assignment_kind=item.assignment_kind,  # type: ignore[arg-type]
            source_activity_id=item.trigger_activity_id,
            source_message_id=item.source_message_id,
            reply_thread_id=task.thread_id,
            priority=item.priority,  # type: ignore[arg-type]
            instruction=item.instruction,
            expected_output=item.expected_output,
            due_at=_as_utc(item.due_at),
            status=item.status,
            result_status=item.result_status,
            result_summary=item.result_summary,
            cancellation_reason=item.cancellation_reason,
            run_status=(latest_run[item.id].status if item.id in latest_run else None),
            run_checkpoint=(latest_run[item.id].checkpoint if item.id in latest_run else {}),
            run_last_heartbeat_at=(
                _as_utc(latest_run[item.id].last_heartbeat_at) if item.id in latest_run else None
            ),
            wake_stage=(
                _run_wake_stage(latest_run[item.id]) if item.id in latest_run else "queued"
            ),  # type: ignore[arg-type]
            created_at=_as_utc(item.created_at),
            updated_at=_as_utc(item.updated_at),
        )
        for item in assignment_rows
    ]
    if activity_limit:
        activity_total = (
            session.scalar(
                select(func.count(TaskActivity.id)).where(TaskActivity.task_id == task.id)
            )
            or 0
        )
        activity_rows = list(
            session.scalars(
                select(TaskActivity)
                .where(TaskActivity.task_id == task.id)
                .where(True if activity_ids is None else TaskActivity.id.in_(activity_ids))
                .order_by(TaskActivity.created_at.desc(), TaskActivity.id.desc())
                .limit(activity_limit)
            )
        )
        activity_relations = list(
            session.scalars(
                select(TaskActivityRelation).where(TaskActivityRelation.task_id == task.id)
            )
        )
    else:
        activity_total = 0
        activity_rows = []
        activity_relations = []
    confirmed_reply_by_child = {
        item.child_activity_id: item for item in activity_relations if item.relation_type == "reply"
    }
    dismissed_reply_suggestion_children = {
        item.child_activity_id
        for item in activity_relations
        if item.relation_type == "dismissed_reply_suggestion"
    }
    projected_metadata: dict[UUID, dict[str, object]] = {}

    def project_activity_metadata(rows: list[TaskActivity]) -> None:
        new_rows = [item for item in rows if item.id not in projected_metadata]
        for item in new_rows:
            metadata = dict(item.activity_metadata)
            relation = confirmed_reply_by_child.get(item.id)
            if relation is not None and "reply_to_activity_id" not in metadata:
                metadata["reply_to_activity_id"] = str(relation.parent_activity_id)
                metadata["reply_relation_source"] = relation.source
                metadata["reply_relation_confirmed_by_human_user_id"] = str(
                    relation.confirmed_by_human_user_id
                )
            if item.id in dismissed_reply_suggestion_children:
                metadata["reply_suggestion_dismissed"] = True
            projected_metadata[item.id] = metadata

        legacy_ids = {
            str(projected_metadata[item.id].get("legacy_reply_message_id"))
            for item in new_rows
            if "reply_to_activity_id" not in projected_metadata[item.id]
            and projected_metadata[item.id].get("legacy_reply_message_id")
        }
        if not legacy_ids:
            return
        replies = {
            message.id: message
            for message in session.scalars(select(Message).where(Message.id.in_(legacy_ids)))
        }
        parent_message_ids = {
            message.reply_to_message_id
            for message in replies.values()
            if message.reply_to_message_id
        }
        parents = {
            message.id: message
            for message in session.scalars(
                select(Message).where(Message.id.in_(parent_message_ids))
            )
        }
        for item in new_rows:
            metadata = projected_metadata[item.id]
            reply = replies.get(str(metadata.get("legacy_reply_message_id")))
            parent = parents.get(reply.reply_to_message_id) if reply is not None else None
            if parent is None or not parent.message_metadata.get("agentpost_task_bridge"):
                continue
            if str(parent.message_metadata.get("agentpost_task_id")) != str(task.id):
                continue
            try:
                parent_activity_id = UUID(
                    str(parent.message_metadata["agentpost_task_activity_id"])
                )
            except (KeyError, TypeError, ValueError):
                continue
            metadata["reply_to_activity_id"] = str(parent_activity_id)
            metadata["reply_relation_source"] = "legacy_task_bridge"

    project_activity_metadata(activity_rows)
    loaded_activity_ids = {item.id for item in activity_rows}
    for _ in range(32 if include_reply_parents else 0):
        missing_parent_ids: set[UUID] = set()
        for metadata in projected_metadata.values():
            parent_id = metadata.get("reply_to_activity_id")
            if not parent_id:
                continue
            try:
                parsed = UUID(str(parent_id))
            except ValueError:
                continue
            if parsed not in loaded_activity_ids:
                missing_parent_ids.add(parsed)
        if not missing_parent_ids:
            break
        parents = list(
            session.scalars(
                select(TaskActivity).where(
                    TaskActivity.task_id == task.id,
                    TaskActivity.id.in_(missing_parent_ids),
                )
            )
        )
        if not parents:
            break
        activity_rows.extend(parents)
        loaded_activity_ids.update(item.id for item in parents)
        project_activity_metadata(parents)
    activity_rows.sort(key=lambda item: (_as_utc(item.created_at), str(item.id)), reverse=True)
    activity_agent_ids = {item.actor_agent_id for item in activity_rows if item.actor_agent_id}
    activity_agents = {
        agent.id: agent
        for agent in session.scalars(select(Agent).where(Agent.id.in_(activity_agent_ids)))
    }
    activities = []
    for item in activity_rows:
        actor_name = None
        actor_agent_name = (
            activity_agents[item.actor_agent_id].display_name
            if item.actor_agent_id in activity_agents
            else None
        )
        actor_human_id = item.actor_human_user_id
        if item.actor_human_user_id in humans:
            actor_name = humans[item.actor_human_user_id].display_name
        elif item.actor_agent_id in activity_agents:
            actor_agent_name = activity_agents[item.actor_agent_id].display_name
            actor_human_id = human_id_by_agent.get(item.actor_agent_id)
            actor_name = (
                humans[actor_human_id].display_name if actor_human_id in humans else "Human 待确认"
            )
        elif item.actor_type == "platform":
            actor_name = "AgentPost"
        target_name = (
            humans[item.target_human_user_id].display_name
            if item.target_human_user_id in humans
            else None
        )
        activities.append(
            TaskActivityResponse(
                activity_id=item.id,
                kind=item.activity_type,
                actor_type=item.actor_type,  # type: ignore[arg-type]
                actor_human_user_id=actor_human_id,
                actor_agent_id=item.actor_agent_id,
                actor_display_name=actor_name,
                actor_agent_display_name=actor_agent_name,
                target_display_name=target_name,
                metadata=projected_metadata[item.id],
                security_label=item.security_label,  # type: ignore[arg-type]
                created_at=_as_utc(item.created_at),
            )
        )
    owner = session.get(HumanUser, task.owner_human_user_id)
    if owner is None:
        raise TaskNotFoundError
    effective_assignment_rows = [
        item
        for item in assignment_rows
        if item.assignment_kind not in {"task_message", "result_sync"}
        and item.cancellation_reason != "legacy_pre_0_1_44_backlog"
    ]
    pending_count = sum(
        item.status not in {"completed", "cancelled"} for item in effective_assignment_rows
    )
    from agentpost.tasks.preferences import preference_summary

    return TaskDetail(
        **preference_summary(session, task.id, viewer_membership.human_user_id),
        task_id=task.id,
        thread_id=task.thread_id,
        title=task.title,
        goal=task.goal,
        expected_output=task.expected_output,
        status=task.status,
        due_at=_as_utc(task.due_at),
        revision=task.revision,
        owner_human_user_id=task.owner_human_user_id,
        owner_display_name=owner.display_name,
        coordinator_agent_id=task.coordinator_agent_id,
        membership_role=viewer_membership.role,  # type: ignore[arg-type]
        membership_status=viewer_membership.status,  # type: ignore[arg-type]
        active_member_count=sum(item.status == "active" for item, _ in membership_rows),
        invited_member_count=sum(item.status == "invited" for item, _ in membership_rows),
        assignment_count=len(effective_assignment_rows),
        pending_assignment_count=pending_count,
        state_axes=_task_state_axes(task, assignments),
        final_summary=task.final_summary,
        created_at=_as_utc(task.created_at),
        updated_at=_as_utc(task.updated_at),
        members=members,
        assignments=assignments,
        activities=activities,
        activity_total=activity_total,
        activities_truncated=activity_total > activity_limit,
    )


def list_tasks(session: Session, *, user: HumanUser, limit: int = 100) -> list[TaskSummary]:
    rows = session.execute(
        select(Task, TaskMembership)
        .join(TaskMembership, TaskMembership.task_id == Task.id)
        .where(
            TaskMembership.human_user_id == user.id,
            TaskMembership.status.in_(["active", "invited"]),
        )
        .order_by(Task.updated_at.desc())
        .limit(limit)
    ).all()
    return [
        TaskSummary.model_validate(
            _task_detail(
                session,
                task=task,
                viewer_membership=membership,
                activity_limit=0,
            ).model_dump(
                exclude={
                    "members",
                    "assignments",
                    "activities",
                    "activity_total",
                    "activities_truncated",
                    "activity_order",
                    "authoritative_source",
                }
            )
        )
        for task, membership in rows
    ]


def get_task(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    activity_limit: int = 200,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user)
    return _task_detail(
        session,
        task=task,
        viewer_membership=membership,
        activity_limit=activity_limit,
    )


def confirm_task_activity_reply(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    payload: TaskActivityReplyRelationCreate,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    child = session.get(TaskActivity, payload.child_activity_id)
    parent = session.get(TaskActivity, payload.parent_activity_id)
    if (
        child is None
        or parent is None
        or child.task_id != task.id
        or parent.task_id != task.id
        or child.id == parent.id
        or child.activity_type != "task_message"
        or parent.created_at > child.created_at
    ):
        raise TaskStateConflictError
    if child.activity_metadata.get("reply_to_activity_id"):
        if payload.decision == "confirm" and str(
            child.activity_metadata["reply_to_activity_id"]
        ) == str(parent.id):
            return _task_detail(session, task=task, viewer_membership=membership)
        raise TaskStateConflictError
    relation_type = "reply" if payload.decision == "confirm" else "dismissed_reply_suggestion"
    existing = session.scalar(
        select(TaskActivityRelation).where(
            TaskActivityRelation.child_activity_id == child.id,
            TaskActivityRelation.relation_type == relation_type,
        )
    )
    if existing is not None:
        if existing.parent_activity_id == parent.id:
            return _task_detail(session, task=task, viewer_membership=membership)
        raise TaskStateConflictError
    confirmed = session.scalar(
        select(TaskActivityRelation).where(
            TaskActivityRelation.child_activity_id == child.id,
            TaskActivityRelation.relation_type == "reply",
        )
    )
    if confirmed is not None:
        raise TaskStateConflictError
    session.add(
        TaskActivityRelation(
            task_id=task.id,
            child_activity_id=child.id,
            parent_activity_id=parent.id,
            relation_type=relation_type,
            source="human_confirmed",
            confirmed_by_human_user_id=user.id,
            created_at=utc_now(),
        )
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action=(
            "task.activity_reply_confirmed"
            if payload.decision == "confirm"
            else "task.activity_reply_suggestion_dismissed"
        ),
        target_type="task_activity",
        target_id=str(child.id),
        outcome="success",
        request_id=request_id,
        audit_metadata={"parent_activity_id": str(parent.id), "task_id": str(task.id)},
    )
    task.updated_at = utc_now()
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def create_task(
    session: Session,
    *,
    user: HumanUser,
    payload: TaskCreate,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    agents = _validate_agent_choice(session, human_id=user.id, choice=payload)
    now = utc_now()
    task = Task(
        owner_human_user_id=user.id,
        coordinator_agent_id=payload.primary_agent_id,
        title=payload.title,
        goal=payload.goal,
        expected_output=payload.expected_output,
        due_at=payload.due_at,
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()
    membership = TaskMembership(
        task_id=task.id,
        human_user_id=user.id,
        primary_agent_id=payload.primary_agent_id,
        agent_selection_source="selected",
        email_notification_status="not_applicable",
        role="owner",
        status="active",
        invited_by_user_id=user.id,
        invited_at=now,
        joined_at=now,
        updated_at=now,
    )
    session.add(membership)
    for agent in agents:
        session.add(
            TaskAgentParticipant(
                task_id=task.id,
                agent_id=agent.id,
                human_user_id=user.id,
                role="primary" if agent.id == payload.primary_agent_id else "support",
                selected_at=now,
            )
        )
        _queue_collaboration_assignment(
            session,
            task=task,
            human_id=user.id,
            agent_id=agent.id,
            created_by_human_id=user.id,
        )
    _add_activity(
        session,
        task_id=task.id,
        kind="task_created",
        actor_type="human",
        actor_human_id=user.id,
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.created",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
        audit_metadata={"agent_ids": [str(agent.id) for agent in agents]},
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def create_task_by_agent(
    session: Session,
    *,
    agent: Agent,
    payload: AgentTaskCreate,
    idempotency_key: str,
) -> TaskDetail:
    owner_id = session.scalar(
        select(AgentOwnership.human_user_id).where(AgentOwnership.agent_id == agent.id)
    )
    owner = session.get(HumanUser, owner_id) if owner_id else None
    if owner is None or owner.status != "active":
        raise TaskAgentSelectionError
    existing = session.scalar(
        select(Task).where(
            Task.coordinator_agent_id == agent.id,
            Task.agent_creation_key == idempotency_key,
        )
    )
    if existing is not None:
        membership = session.get(TaskMembership, (existing.id, owner.id))
        if membership is None:
            raise TaskNotFoundError
        return _task_detail(session, task=existing, viewer_membership=membership)
    now = utc_now()
    task = Task(
        owner_human_user_id=owner.id,
        coordinator_agent_id=agent.id,
        agent_creation_key=idempotency_key,
        title=payload.title,
        goal=payload.goal,
        expected_output=payload.expected_output,
        due_at=payload.due_at,
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()
    membership = TaskMembership(
        task_id=task.id,
        human_user_id=owner.id,
        primary_agent_id=agent.id,
        agent_selection_source="selected",
        email_notification_status="not_applicable",
        role="owner",
        status="active",
        invited_by_user_id=owner.id,
        invited_at=now,
        joined_at=now,
        updated_at=now,
    )
    session.add(membership)
    session.add(
        TaskAgentParticipant(
            task_id=task.id,
            agent_id=agent.id,
            human_user_id=owner.id,
            role="primary",
            selected_at=now,
        )
    )
    _queue_collaboration_assignment(
        session,
        task=task,
        human_id=owner.id,
        agent_id=agent.id,
        created_by_human_id=owner.id,
    )
    _add_activity(
        session,
        task_id=task.id,
        kind="task_created",
        actor_type="agent",
        actor_agent_id=agent.id,
        metadata={
            "created_for_human_user_id": str(owner.id),
            "publication_origin": payload.publication_origin,
        },
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def _normalize_task_reference(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def resolve_task_for_agent(
    session: Session,
    *,
    agent: Agent,
    query: str,
    candidate_limit: int = 5,
) -> AgentTaskResolution:
    rows = session.execute(
        select(Task, TaskMembership, HumanUser)
        .join(
            TaskAgentParticipant,
            TaskAgentParticipant.task_id == Task.id,
        )
        .join(
            TaskMembership,
            (TaskMembership.task_id == Task.id)
            & (TaskMembership.human_user_id == TaskAgentParticipant.human_user_id),
        )
        .join(HumanUser, HumanUser.id == Task.owner_human_user_id)
        .where(
            TaskAgentParticipant.agent_id == agent.id,
            TaskAgentParticipant.active.is_(True),
            TaskMembership.status == "active",
        )
        .order_by(Task.updated_at.desc(), Task.id)
    ).all()
    normalized_query = _normalize_task_reference(query)

    def candidate(row, *, match_kind: str) -> AgentTaskCandidate:
        task, membership, owner = row
        return AgentTaskCandidate(
            task_id=task.id,
            thread_id=task.thread_id,
            title=task.title,
            owner_human_user_id=owner.id,
            owner_display_name=owner.display_name,
            status=task.status,
            membership_role=membership.role,  # type: ignore[arg-type]
            updated_at=_as_utc(task.updated_at),
            label=f"{task.title} · {owner.display_name} · {task.status}",
            match_kind=match_kind,  # type: ignore[arg-type]
        )

    exact_rows = [
        row for row in rows if _normalize_task_reference(row[0].title) == normalized_query
    ]
    if len(exact_rows) == 1:
        return AgentTaskResolution(
            status="resolved",
            query=query,
            match=candidate(exact_rows[0], match_kind="exact"),
            total_candidates=1,
            reason="unique_exact_title",
        )
    if exact_rows:
        return AgentTaskResolution(
            status="needs_clarification",
            query=query,
            candidates=[candidate(row, match_kind="exact") for row in exact_rows[:candidate_limit]],
            total_candidates=len(exact_rows),
            reason="duplicate_exact_title",
        )

    partial_rows = [
        row
        for row in rows
        if normalized_query in _normalize_task_reference(row[0].title)
        or _normalize_task_reference(row[0].title) in normalized_query
    ]
    if partial_rows:
        return AgentTaskResolution(
            status="needs_clarification",
            query=query,
            candidates=[
                candidate(row, match_kind="partial") for row in partial_rows[:candidate_limit]
            ],
            total_candidates=len(partial_rows),
            reason="partial_title_requires_confirmation",
        )
    return AgentTaskResolution(
        status="not_found",
        query=query,
        reason="no_participating_task_match",
    )


def _task_participation_for_agent(
    session: Session, *, agent: Agent, task_id: UUID
) -> tuple[Task, TaskAgentParticipant, TaskMembership]:
    row = session.execute(
        select(Task, TaskAgentParticipant, TaskMembership)
        .join(TaskAgentParticipant, TaskAgentParticipant.task_id == Task.id)
        .join(
            TaskMembership,
            (TaskMembership.task_id == Task.id)
            & (TaskMembership.human_user_id == TaskAgentParticipant.human_user_id),
        )
        .where(
            Task.id == task_id,
            TaskAgentParticipant.agent_id == agent.id,
            TaskAgentParticipant.active.is_(True),
            TaskMembership.status == "active",
        )
    ).one_or_none()
    if row is None:
        raise TaskNotFoundError
    return row


def cancel_queued_assignment(
    session: Session, *, user: HumanUser, task_id: UUID, assignment_id: UUID
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    assignment = session.scalar(
        select(TaskAssignment)
        .where(TaskAssignment.id == assignment_id, TaskAssignment.task_id == task_id)
        .with_for_update()
    )
    if assignment is None:
        raise TaskNotFoundError
    if assignment.status == "cancelled":
        return _task_detail(session, task=task, viewer_membership=membership)
    runs = list(
        session.scalars(
            select(AgentRun).where(AgentRun.assignment_id == assignment_id).with_for_update()
        )
    )
    if assignment.status != "queued" or any(
        run.status in {"leased", "starting", "running", "waiting_human"} for run in runs
    ):
        raise TaskStateConflictError
    now = utc_now()
    assignment.status = "cancelled"
    assignment.cancellation_reason = "human_cancelled"
    assignment.updated_at = now
    for run in runs:
        if run.status == "queued":
            run.status = "cancelled"
            run.cancellation_reason = "human_cancelled"
            run.finished_at = now
            run.lease_token_digest = None
            run.lease_expires_at = None
    task.updated_at = now
    _add_activity(
        session,
        task_id=task_id,
        kind="assignment_cancelled",
        actor_type="human",
        actor_human_id=user.id,
        metadata={
            "assignment_id": str(assignment_id),
            "reason": "human_cancelled",
            "previous_status": "queued",
        },
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def agent_handshake(session: Session, *, agent: Agent, limit: int = 50) -> dict:
    """Small authorized task index; no history or execution side effects."""
    from agentpost import __version__

    rows = list(
        session.scalars(
            select(Task)
            .join(TaskAgentParticipant, TaskAgentParticipant.task_id == Task.id)
            .join(
                TaskMembership,
                (TaskMembership.task_id == Task.id)
                & (TaskMembership.human_user_id == TaskAgentParticipant.human_user_id),
            )
            .where(
                TaskAgentParticipant.agent_id == agent.id,
                TaskAgentParticipant.active.is_(True),
                TaskMembership.status == "active",
            )
            .order_by(Task.updated_at.desc(), Task.id.desc())
            .limit(limit + 1)
        )
    )
    connection = session.scalar(
        select(ConnectorInstance)
        .join(
            AgentConnectorBinding,
            AgentConnectorBinding.connector_instance_id == ConnectorInstance.id,
        )
        .where(AgentConnectorBinding.agent_id == agent.id, ConnectorInstance.status == "active")
    )
    return {
        "agent_id": agent.id,
        "agent_name": agent.display_name,
        "server_version": __version__,
        "connection": {
            "runtime_version": connection.runtime_version,
            "last_heartbeat_at": _as_utc(connection.last_heartbeat_at),
            "runtime_capabilities": connection.runtime_capabilities,
            "health_status": connection.health_status,
        }
        if connection
        else None,
        "tasks_truncated": len(rows) > limit,
        "tasks": [
            {
                "task_id": task.id,
                "title": task.title,
                "status": task.status,
                "updated_at": _as_utc(task.updated_at),
            }
            for task in rows[:limit]
        ],
        "authoritative_source": "task_activities",
        "contract": "/api/v1/protocol/contract",
        "next_steps": ["resolve_task_if_title", "get_task", "task_activities"],
        "automatic_wake": "host_dependent_unverified",
        "security_label": "external_agent_content",
    }


def get_task_for_agent(
    session: Session, *, agent: Agent, task_id: UUID, include_history: bool = True
) -> TaskDetail:
    task, _, membership = _task_participation_for_agent(session, agent=agent, task_id=task_id)
    detail = _task_detail(
        session,
        task=task,
        viewer_membership=membership,
        activity_limit=200 if include_history else 0,
    )
    if not include_history:
        detail.activity_total = (
            session.scalar(
                select(func.count(TaskActivity.id)).where(TaskActivity.task_id == task_id)
            )
            or 0
        )
        detail.activities_truncated = detail.activity_total > 0
    return detail


def read_agent_activity_page(
    session: Session,
    *,
    agent: Agent,
    task_id: UUID,
    cursor: UUID | None = None,
    limit: int = 50,
    activity_id: UUID | None = None,
) -> dict:
    """Authorized keyset read. Parent context is fetched separately, never injected into pages."""
    task, _, membership = _task_participation_for_agent(session, agent=agent, task_id=task_id)
    query = select(TaskActivity).where(TaskActivity.task_id == task_id)
    if activity_id is not None:
        query = query.where(TaskActivity.id == activity_id)
    if cursor is not None:
        anchor = session.scalar(
            select(TaskActivity).where(TaskActivity.task_id == task_id, TaskActivity.id == cursor)
        )
        if anchor is None:
            raise TaskNotFoundError
        query = query.where(TaskActivity.sequence > anchor.sequence)
    rows = list(session.scalars(query.order_by(TaskActivity.sequence.asc()).limit(limit + 1)))
    if activity_id is not None and not rows:
        raise TaskNotFoundError
    selected = rows[:limit]
    detail = _task_detail(
        session,
        task=task,
        viewer_membership=membership,
        activity_limit=limit,
        activity_ids=[row.id for row in selected],
        include_reply_parents=False,
        include_assignments=False,
    )
    return {
        "task_id": task_id,
        "items": sorted(
            detail.activities,
            key=lambda item: next(row.sequence for row in selected if row.id == item.activity_id),
        ),
        "order": "task_sequence_asc",
        "has_more": len(rows) > limit,
        "next_cursor": str(selected[-1].id) if selected else (str(cursor) if cursor else None),
        "security_label": "external_agent_content",
    }


def _connector_version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    matched = re.fullmatch(r"(?:agentpost-connect/)?([0-9]+)\.([0-9]+)\.([0-9]+)", value.strip())
    if matched is None:
        return None
    return tuple(int(part) for part in matched.groups())  # type: ignore[return-value]


def _supports_native_task_messages(session: Session, *, agent_id: UUID) -> bool:
    connector = session.execute(
        select(ConnectorInstance.runtime_version, ConnectorInstance.runtime_capabilities)
        .join(
            AgentConnectorBinding,
            AgentConnectorBinding.connector_instance_id == ConnectorInstance.id,
        )
        .where(
            AgentConnectorBinding.agent_id == agent_id,
            ConnectorInstance.status == "active",
        )
    ).one_or_none()
    if connector is None:
        return False
    runtime_version, capabilities = connector
    parsed = _connector_version_tuple(runtime_version)
    return "task_message_send" in capabilities or (parsed is not None and parsed >= (0, 1, 40))


def _legacy_task_delivery(
    session: Session,
    *,
    task: Task,
    activity: TaskActivity,
    sender_agent_id: UUID,
    recipient_agent_id: UUID,
    subject: str,
    content_format: str,
    body: object,
    source_message_id: str,
) -> Message:
    now = utc_now()
    message = Message(
        id=f"msg_{secrets.token_hex(16)}",
        sender_agent_id=sender_agent_id,
        subject=subject or f"任务更新：{task.title}",
        content_format=content_format,
        content_body=body,
        message_type="notification",
        priority="normal",
        thread_id=task.thread_id,
        reply_to_message_id=None,
        requires_ack=True,
        task_payload=None,
        result_payload=None,
        message_metadata={
            "agentpost_task_bridge": True,
            "agentpost_task_id": str(task.id),
            "agentpost_task_activity_id": str(activity.id),
            "agentpost_task_title": task.title,
            "agentpost_task_source_message_id": source_message_id,
        },
        accepted_at=now,
        created_at=now,
        expires_at=None,
    )
    session.add(message)
    session.add(
        Delivery(
            message=message,
            recipient_agent_id=recipient_agent_id,
            delivery_status="delivered",
            delivery_attempts=1,
            last_attempt_at=now,
            delivered_at=now,
            created_at=now,
        )
    )
    return message


def _fanout_task_message(
    session: Session,
    *,
    task: Task,
    activity: TaskActivity,
    sender_agent_id: UUID,
    subject: str,
    content_format: str,
    body: object,
    source_message_id: str,
    already_delivered_agent_ids: set[UUID] | None = None,
) -> tuple[int, int, list[Message], list[dict[str, str]]]:
    queued_runs = 0
    legacy_deliveries = 0
    legacy_messages: list[Message] = []
    recipient_statuses: list[dict[str, str]] = []
    already_delivered_agent_ids = already_delivered_agent_ids or set()
    participants = list(
        session.scalars(
            select(TaskAgentParticipant).where(
                TaskAgentParticipant.task_id == task.id,
                TaskAgentParticipant.active.is_(True),
                TaskAgentParticipant.agent_id != sender_agent_id,
            )
        )
    )
    for participant in participants:
        if _supports_native_task_messages(session, agent_id=participant.agent_id):
            recipient_statuses.append(
                {
                    "human_user_id": str(participant.human_user_id),
                    "agent_id": str(participant.agent_id),
                    "status": "context_available",
                }
            )
        elif participant.agent_id not in already_delivered_agent_ids:
            legacy_message = _legacy_task_delivery(
                session,
                task=task,
                activity=activity,
                sender_agent_id=sender_agent_id,
                recipient_agent_id=participant.agent_id,
                subject=subject,
                content_format=content_format,
                body=body,
                source_message_id=source_message_id,
            )
            legacy_messages.append(legacy_message)
            legacy_deliveries += 1
            recipient_statuses.append(
                {
                    "human_user_id": str(participant.human_user_id),
                    "agent_id": str(participant.agent_id),
                    "status": "legacy_delivered",
                }
            )
    return queued_runs, legacy_deliveries, legacy_messages, recipient_statuses


def send_task_message_by_human(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    body: str,
    parent_id: UUID,
    references: list[UUID],
    idempotency_key: str,
) -> AgentTaskMessageResponse:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.status != "active":
        raise TaskNotFoundError
    metadata = _task_reply_metadata(
        session,
        task_id=task.id,
        parent_id=parent_id,
        references=references,
    )
    metadata.update({"body": body, "content_format": "text", "publication_origin": "human_direct"})
    request_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    activity_id = uuid5(user.id, f"task-message:{task.id}:{idempotency_key}")
    existing = session.get(TaskActivity, activity_id)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise TaskMessageIdempotencyConflictError
    else:
        activity = _add_activity(
            session,
            task_id=task.id,
            kind="task_message",
            actor_type="human",
            actor_human_id=user.id,
            metadata=metadata,
            external=True,
            request_hash=request_hash,
        )
        activity.id = activity_id
        task.updated_at = utc_now()
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.get(TaskActivity, activity_id)
            if existing is None:
                raise
            if existing.request_hash != request_hash:
                raise TaskMessageIdempotencyConflictError from None
    return AgentTaskMessageResponse(
        task_id=task.id,
        thread_id=task.thread_id,
        activity_id=activity_id,
        queued_run_count=0,
        legacy_delivery_count=0,
        attachment_ids=[],
        replayed=existing is not None,
    )


def _task_reply_metadata(
    session: Session, *, task_id: UUID, parent_id: UUID | None, references: list[UUID]
) -> dict[str, object]:
    ids = set(references) | ({parent_id} if parent_id else set())
    records = {
        item.id: item
        for item in session.scalars(
            select(TaskActivity).where(TaskActivity.task_id == task_id, TaskActivity.id.in_(ids))
        )
    }
    if ids != set(records):
        raise TaskNotFoundError
    metadata: dict[str, object] = {}
    if parent_id:
        parent = records[parent_id]
        metadata["reply_to_activity_id"] = str(parent_id)
        metadata["discussion_root_activity_id"] = parent.activity_metadata.get(
            "discussion_root_activity_id", str(parent_id)
        )
    if references:
        metadata["referenced_activity_ids"] = list(dict.fromkeys(str(item) for item in references))
    return metadata


def send_task_message_by_agent(
    session: Session,
    *,
    agent: Agent,
    task_id: UUID,
    payload: AgentTaskMessageCreate,
    idempotency_key: str,
) -> AgentTaskMessageResponse:
    task, _, _ = _task_participation_for_agent(session, agent=agent, task_id=task_id)
    reply_metadata = _task_reply_metadata(
        session,
        task_id=task.id,
        parent_id=payload.reply_to_activity_id,
        references=payload.referenced_activity_ids,
    )
    hash_payload = payload.model_dump(mode="json")
    if payload.reply_to_activity_id is None:
        hash_payload.pop("reply_to_activity_id")
    if not payload.referenced_activity_ids:
        hash_payload.pop("referenced_activity_ids")
    request_hash = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    existing = session.scalar(
        select(TaskActivity).where(
            TaskActivity.actor_agent_id == agent.id,
            TaskActivity.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash or existing.task_id != task.id:
            raise TaskMessageIdempotencyConflictError
        return AgentTaskMessageResponse(
            task_id=task.id,
            thread_id=task.thread_id,
            activity_id=existing.id,
            queued_run_count=int(existing.activity_metadata.get("queued_run_count", 0)),
            legacy_delivery_count=int(existing.activity_metadata.get("legacy_delivery_count", 0)),
            attachment_ids=[
                UUID(value) for value in existing.activity_metadata.get("attachment_ids", [])
            ],
            replayed=True,
        )
    source_message_id = f"msg_{secrets.token_hex(16)}"
    activity = _add_activity(
        session,
        task_id=task.id,
        kind="task_message",
        actor_type="agent",
        actor_agent_id=agent.id,
        metadata={
            "subject": payload.subject,
            "content_format": payload.content_format,
            "body": payload.body,
            "source_message_id": source_message_id,
            "attachment_ids": [str(value) for value in payload.attachments],
            "publication_origin": payload.publication_origin,
            **reply_metadata,
        },
        external=True,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(TaskActivity).where(
                TaskActivity.actor_agent_id == agent.id,
                TaskActivity.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        if existing.request_hash != request_hash or existing.task_id != task.id:
            raise TaskMessageIdempotencyConflictError from None
        return AgentTaskMessageResponse(
            task_id=task.id,
            thread_id=task.thread_id,
            activity_id=existing.id,
            queued_run_count=int(existing.activity_metadata.get("queued_run_count", 0)),
            legacy_delivery_count=int(existing.activity_metadata.get("legacy_delivery_count", 0)),
            attachment_ids=[
                UUID(value) for value in existing.activity_metadata.get("attachment_ids", [])
            ],
            replayed=True,
        )
    source_message = Message(
        id=source_message_id,
        sender_agent_id=agent.id,
        subject=payload.subject or f"任务更新：{task.title}",
        content_format=payload.content_format,
        content_body=payload.body,
        message_type="notification",
        priority="normal",
        thread_id=task.thread_id,
        reply_to_message_id=(
            session.get(TaskActivity, payload.reply_to_activity_id).activity_metadata.get(
                "source_message_id"
            )
            if payload.reply_to_activity_id
            else None
        ),
        requires_ack=False,
        task_payload=None,
        result_payload=None,
        message_metadata={
            "agentpost_task_source": True,
            "agentpost_task_id": str(task.id),
            "agentpost_task_activity_id": str(activity.id),
        },
        accepted_at=utc_now(),
        created_at=utc_now(),
        expires_at=None,
    )
    session.add(source_message)
    session.flush()
    queued_runs, legacy_deliveries, legacy_messages, recipient_statuses = _fanout_task_message(
        session,
        task=task,
        activity=activity,
        sender_agent_id=agent.id,
        subject=payload.subject,
        content_format=payload.content_format,
        body=payload.body,
        source_message_id=source_message_id,
    )
    bind_attachments(
        session,
        sender=agent,
        attachment_ids=payload.attachments,
        message_id=source_message_id,
        visible_message_ids=[source_message_id, *[message.id for message in legacy_messages]],
    )
    attachments = list(
        session.scalars(select(Attachment).where(Attachment.id.in_(payload.attachments)))
    )
    activity.activity_metadata = {
        **activity.activity_metadata,
        "queued_run_count": queued_runs,
        "legacy_delivery_count": legacy_deliveries,
        "recipient_statuses": recipient_statuses,
        "attachments": [attachment_metadata(item) for item in attachments],
    }
    task.updated_at = utc_now()
    session.commit()
    return AgentTaskMessageResponse(
        task_id=task.id,
        thread_id=task.thread_id,
        activity_id=activity.id,
        queued_run_count=queued_runs,
        legacy_delivery_count=legacy_deliveries,
        attachment_ids=payload.attachments,
    )


def record_legacy_task_reply(
    session: Session,
    *,
    agent: Agent,
    parent: Message,
    reply: Message,
) -> None:
    if not parent.message_metadata.get("agentpost_task_bridge"):
        return
    try:
        task_id = UUID(str(parent.message_metadata["agentpost_task_id"]))
    except (KeyError, TypeError, ValueError):
        return
    try:
        task, _, _ = _task_participation_for_agent(session, agent=agent, task_id=task_id)
    except TaskNotFoundError:
        return
    try:
        parent_activity_id = UUID(str(parent.message_metadata["agentpost_task_activity_id"]))
    except (KeyError, TypeError, ValueError):
        return
    try:
        reply_metadata = _task_reply_metadata(
            session,
            task_id=task.id,
            parent_id=parent_activity_id,
            references=[],
        )
    except TaskNotFoundError:
        return
    activity = _add_activity(
        session,
        task_id=task.id,
        kind="task_message",
        actor_type="agent",
        actor_agent_id=agent.id,
        metadata={
            "subject": reply.subject,
            "content_format": reply.content_format,
            "body": reply.content_body,
            "legacy_reply_message_id": reply.id,
            "source_message_id": reply.id,
            "publication_origin": "agent_autonomous",
            "reply_relation_source": "legacy_task_bridge",
            **reply_metadata,
        },
        external=True,
    )
    session.flush()
    _, _, _, recipient_statuses = _fanout_task_message(
        session,
        task=task,
        activity=activity,
        sender_agent_id=agent.id,
        subject=reply.subject,
        content_format=reply.content_format,
        body=reply.content_body,
        source_message_id=reply.id,
        already_delivered_agent_ids={parent.sender_agent_id},
    )
    activity.activity_metadata = {
        **activity.activity_metadata,
        "recipient_statuses": recipient_statuses,
    }
    task.updated_at = utc_now()


def list_task_invitation_candidates(
    session: Session, *, user: HumanUser, task_id: UUID, limit: int = 100
) -> list[FriendResponse]:
    task, membership = _task_context(session, task_id=task_id, user=user)
    if membership.status != "active" or task.status not in {"active", "paused"}:
        raise TaskNotFoundError
    existing = set(
        session.scalars(
            select(TaskMembership.human_user_id).where(
                TaskMembership.task_id == task_id,
                TaskMembership.status.in_(["active", "invited"]),
            )
        )
    )
    return [
        friend
        for friend in list_friends(session, user=user, limit=limit)
        if friend.relation_status == "accepted" and friend.human_user_id not in existing
    ]


def invite_task_members(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    human_user_ids: list[UUID],
    human_session_id: UUID | None,
    request_id: str,
    settings: Settings,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.status != "active" or task.status not in {"active", "paused"}:
        raise TaskNotFoundError
    accepted_ids = {
        friend.human_user_id
        for friend in list_friends(session, user=user, limit=200)
        if friend.relation_status == "accepted"
    }
    if not set(human_user_ids).issubset(accepted_ids):
        raise FriendshipNotFoundError
    existing_ids = set(
        session.scalars(
            select(TaskMembership.human_user_id).where(
                TaskMembership.task_id == task_id,
                TaskMembership.status.in_(["active", "invited"]),
            )
        )
    )
    if existing_ids.intersection(human_user_ids):
        raise TaskStateConflictError
    humans = {
        human.id: human
        for human in session.scalars(
            select(HumanUser).where(HumanUser.id.in_(human_user_ids), HumanUser.status == "active")
        )
    }
    default_agents: dict[UUID, Agent] = {}
    for human_id in human_user_ids:
        human = humans.get(human_id)
        if human is None or human.default_agent_id is None:
            raise TaskAgentSelectionError
        default_agent = _human_agent(session, human_id, human.default_agent_id)
        if default_agent is None:
            raise TaskAgentSelectionError
        default_agents[human_id] = default_agent
    now = utc_now()
    for human_id in human_user_ids:
        default_agent = default_agents[human_id]
        row = session.get(TaskMembership, (task_id, human_id))
        if row is None:
            row = TaskMembership(task_id=task_id, human_user_id=human_id)
        row.primary_agent_id = default_agent.id
        row.agent_selection_source = "default"
        row.email_notification_status = "pending"
        row.email_notification_attempts = 0
        row.email_notified_at = None
        row.role = "member"
        row.status = "active"
        row.invited_by_user_id = user.id
        row.invited_at = now
        row.joined_at = now
        row.updated_at = now
        session.add(row)
        participant = session.get(TaskAgentParticipant, (task.id, default_agent.id))
        if participant is None:
            participant = TaskAgentParticipant(
                task_id=task.id,
                agent_id=default_agent.id,
                human_user_id=human_id,
                role="primary",
                selected_at=now,
            )
            session.add(participant)
        participant.active = True
        participant.role = "primary"
        participant.selected_at = now
        _queue_collaboration_assignment(
            session,
            task=task,
            human_id=human_id,
            agent_id=default_agent.id,
            created_by_human_id=user.id,
        )
        _add_activity(
            session,
            task_id=task_id,
            kind="member_added",
            actor_type="human",
            actor_human_id=user.id,
            target_human_id=human_id,
            metadata={"agent_id": str(default_agent.id), "selection_source": "default"},
        )
    task.updated_at = now
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.members_added",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    session.commit()
    for human_id in human_user_ids:
        human = humans[human_id]
        default_agent = default_agents[human_id]
        row = session.get(TaskMembership, (task_id, human_id))
        if row is None:
            continue
        row.email_notification_attempts += 1
        try:
            deliver_task_membership_notification(
                settings,
                email=human.email,
                inviter_name=user.display_name,
                task_title=task.title,
                task_id=str(task.id),
                agent_name=default_agent.display_name,
            )
        except EmailDeliveryError:
            row.email_notification_status = "failed"
            _add_activity(
                session,
                task_id=task.id,
                kind="member_email_failed",
                actor_type="platform",
                target_human_id=human_id,
            )
        else:
            row.email_notification_status = "sent"
            row.email_notified_at = utc_now()
            _add_activity(
                session,
                task_id=task.id,
                kind="member_email_sent",
                actor_type="platform",
                target_human_id=human_id,
            )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def select_task_agents(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    choice: AgentChoice,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.status != "active" or task.status not in {"active", "paused"}:
        raise TaskStateConflictError
    agents = _validate_agent_choice(session, human_id=user.id, choice=choice)
    now = utc_now()
    existing = list(
        session.scalars(
            select(TaskAgentParticipant).where(
                TaskAgentParticipant.task_id == task.id,
                TaskAgentParticipant.human_user_id == user.id,
            )
        )
    )
    selected_ids = {agent.id for agent in agents}
    previously_active_ids = {participant.agent_id for participant in existing if participant.active}
    removed_ids = previously_active_ids - selected_ids
    for participant in existing:
        participant.active = participant.agent_id in selected_ids
        if participant.active:
            participant.role = (
                "primary" if participant.agent_id == choice.primary_agent_id else "support"
            )
    existing_ids = {participant.agent_id for participant in existing}
    if removed_ids:
        removed_assignments = list(
            session.scalars(
                select(TaskAssignment).where(
                    TaskAssignment.task_id == task.id,
                    TaskAssignment.responsible_human_user_id == user.id,
                    TaskAssignment.assignee_agent_id.in_(removed_ids),
                    TaskAssignment.status.in_(["queued", "running", "waiting_human"]),
                )
            )
        )
        for assignment in removed_assignments:
            assignment.status = "cancelled"
            assignment.updated_at = now
            for run in session.scalars(
                select(AgentRun).where(
                    AgentRun.assignment_id == assignment.id,
                    AgentRun.status.in_(
                        ["queued", "leased", "starting", "running", "waiting_human"]
                    ),
                )
            ):
                run.status = "cancelled"
                run.finished_at = now
                run.lease_expires_at = None
                run.lease_token_digest = None
    for agent in agents:
        if agent.id not in existing_ids:
            session.add(
                TaskAgentParticipant(
                    task_id=task.id,
                    agent_id=agent.id,
                    human_user_id=user.id,
                    role="primary" if agent.id == choice.primary_agent_id else "support",
                    selected_at=now,
                )
            )
        if agent.id not in previously_active_ids:
            _queue_collaboration_assignment(
                session,
                task=task,
                human_id=user.id,
                agent_id=agent.id,
                created_by_human_id=user.id,
            )
    membership.primary_agent_id = choice.primary_agent_id
    membership.agent_selection_source = "selected"
    membership.updated_at = now
    task.updated_at = now
    _add_activity(
        session,
        task_id=task.id,
        kind="member_agents_selected",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=user.id,
        metadata={"agent_ids": [str(agent.id) for agent in agents]},
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.agents_selected",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def decide_task_invitation(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    accept: bool,
    choice: AgentChoice | None,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail | None:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.status != "invited":
        raise TaskStateConflictError
    agents: list[Agent] = []
    if accept:
        if choice is None:
            raise TaskAgentSelectionError
        agents = _validate_agent_choice(session, human_id=user.id, choice=choice)
    now = utc_now()
    membership.status = "active" if accept else "declined"
    membership.primary_agent_id = choice.primary_agent_id if accept and choice else None
    membership.agent_selection_source = "selected"
    membership.joined_at = now if accept else None
    membership.updated_at = now
    for agent in agents:
        session.add(
            TaskAgentParticipant(
                task_id=task.id,
                agent_id=agent.id,
                human_user_id=user.id,
                role="primary" if choice and agent.id == choice.primary_agent_id else "support",
                selected_at=now,
            )
        )
        _queue_collaboration_assignment(
            session,
            task=task,
            human_id=user.id,
            agent_id=agent.id,
            created_by_human_id=user.id,
        )
    _add_activity(
        session,
        task_id=task.id,
        kind="member_joined" if accept else "member_declined",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=user.id,
        metadata={"agent_ids": [str(agent.id) for agent in agents]},
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.invitation_accepted" if accept else "task.invitation_declined",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    task.updated_at = now
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership) if accept else None


def _validate_assignment_target(
    session: Session, task_id: UUID, payload: TaskAssignmentCreate
) -> None:
    target_membership = session.get(TaskMembership, (task_id, payload.responsible_human_user_id))
    participant = session.get(TaskAgentParticipant, (task_id, payload.assignee_agent_id))
    if (
        target_membership is None
        or target_membership.status != "active"
        or participant is None
        or not participant.active
        or participant.human_user_id != payload.responsible_human_user_id
    ):
        raise TaskAgentSelectionError


def _create_assignment_work(
    session: Session,
    *,
    task: Task,
    user: HumanUser,
    payload: TaskAssignmentCreate,
    human_session_id: UUID | None,
    request_id: str,
    activity_id: UUID | None = None,
    request_hash: str | None = None,
    batch_id: UUID | None = None,
) -> None:
    task_id = task.id
    source_activity = _add_activity(
        session,
        task_id=task_id,
        kind="assignment_created",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=payload.responsible_human_user_id,
        metadata={"assignee_agent_id": str(payload.assignee_agent_id)},
    )
    if activity_id is not None:
        source_activity.id = activity_id
        source_activity.request_hash = request_hash
        source_activity.activity_metadata["batch_id"] = str(batch_id)
    session.flush()
    assignment = _queue_collaboration_assignment(
        session,
        task=task,
        human_id=payload.responsible_human_user_id,
        agent_id=payload.assignee_agent_id,
        created_by_human_id=user.id,
        assignment_kind="human_directed",
        trigger_activity_id=source_activity.id,
        priority=payload.priority,
        instruction=payload.instruction,
        expected_output=payload.expected_output,
        due_at=payload.due_at,
    )
    source_activity.activity_metadata = {
        **source_activity.activity_metadata,
        "assignment_id": str(assignment.id),
        "instruction": assignment.instruction,
        "expected_output": assignment.expected_output,
        "priority": assignment.priority,
    }
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.assignment_created",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )


def create_assignment(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    payload: TaskAssignmentCreate,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    if task.status != "active":
        raise TaskStateConflictError
    _validate_assignment_target(session, task_id, payload)
    _create_assignment_work(
        session,
        task=task,
        user=user,
        payload=payload,
        human_session_id=human_session_id,
        request_id=request_id,
    )
    task.updated_at = utc_now()
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def create_assignment_batch(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    payload: TaskAssignmentBatchCreate,
    idempotency_key: str,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    batch_id = uuid5(user.id, f"task-assignment-batch:{task_id}:{idempotency_key}")
    request_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    # The first work activity doubles as the atomic batch receipt, even after members change.
    existing = session.get(TaskActivity, batch_id)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise TaskMessageIdempotencyConflictError
        return _task_detail(session, task=task, viewer_membership=membership)
    if task.status != "active":
        raise TaskStateConflictError
    common = payload.model_dump(exclude={"assignees"})
    assignments = [
        TaskAssignmentCreate(**common, **target.model_dump()) for target in payload.assignees
    ]
    for item in assignments:
        _validate_assignment_target(session, task_id, item)
    try:
        for index, item in enumerate(assignments):
            _create_assignment_work(
                session,
                task=task,
                user=user,
                payload=item,
                human_session_id=human_session_id,
                request_id=request_id,
                activity_id=batch_id
                if index == 0
                else uuid5(batch_id, str(item.assignee_agent_id)),
                request_hash=request_hash,
                batch_id=batch_id,
            )
        task.updated_at = utc_now()
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.get(TaskActivity, batch_id)
        if existing is None:
            raise
        if existing.request_hash != request_hash:
            raise TaskMessageIdempotencyConflictError from None
    return _task_detail(session, task=task, viewer_membership=membership)


def respond_to_waiting_agent_run(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    assignment_id: UUID,
    payload: TaskRunHumanResponse,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.status != "active" or task.status != "active":
        raise TaskStateConflictError
    assignment = session.scalar(
        select(TaskAssignment)
        .where(TaskAssignment.id == assignment_id, TaskAssignment.task_id == task_id)
        .with_for_update()
    )
    if assignment is None:
        raise TaskNotFoundError
    if user.id not in {task.owner_human_user_id, assignment.responsible_human_user_id}:
        raise TaskHumanResponseForbiddenError
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.assignment_id == assignment.id)
        .order_by(AgentRun.attempt.desc())
        .with_for_update()
        .limit(1)
    )
    if run is None or run.status != "waiting_human" or assignment.status != "waiting_human":
        raise TaskStateConflictError

    now = utc_now()
    previous_checkpoint = run.checkpoint if isinstance(run.checkpoint, dict) else {}
    run.status = "interrupted"
    run.finished_at = now
    run.lease_expires_at = None
    run.lease_token_digest = None
    run.cancellation_reason = "human_response_superseded"
    successor = AgentRun(
        assignment_id=assignment.id,
        agent_id=assignment.assignee_agent_id,
        attempt=run.attempt + 1,
        checkpoint={
            "previous_checkpoint": previous_checkpoint,
            "human_response": payload.response,
            "responded_by_human_user_id": str(user.id),
            "responded_at": now.isoformat(),
        },
    )
    session.add(successor)
    assignment.status = "queued"
    assignment.updated_at = now
    activity = _add_activity(
        session,
        task_id=task.id,
        kind="human_run_response",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=assignment.responsible_human_user_id,
        metadata={
            "assignment_id": str(assignment.id),
            "previous_run_id": str(run.id),
            "response": payload.response,
        },
    )
    session.flush()
    activity.activity_metadata = {
        **activity.activity_metadata,
        "successor_run_id": str(successor.id),
    }
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.run_human_response",
        target_type="task_assignment",
        target_id=str(assignment.id),
        outcome="success",
        request_id=request_id,
    )
    task.updated_at = now
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def update_task_status(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    action: str,
    reason: str | None,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    transitions = {
        "pause": ({"active"}, "paused"),
        "resume": ({"paused"}, "active"),
        "cancel": ({"active", "paused", "awaiting_acceptance"}, "cancelled"),
        "archive": ({"completed", "cancelled"}, "archived"),
        "restore": ({"archived"}, "completed" if task.completed_at else "cancelled"),
    }
    allowed, target = transitions[action]
    if task.status not in allowed:
        raise TaskStateConflictError
    now = utc_now()
    task.status = target
    task.updated_at = now
    if action == "cancel":
        task.cancelled_at = now
    if action == "archive":
        task.archived_at = now
    if action == "restore":
        task.archived_at = None
    _add_activity(
        session,
        task_id=task.id,
        kind=f"task_{action}",
        actor_type="human",
        actor_human_id=user.id,
        metadata={"reason": reason} if reason else {},
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action=f"task.{action}",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def submit_task(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    payload: TaskFinalSubmission,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    if task.status != "active":
        raise TaskStateConflictError
    if session.scalar(
        select(func.count(TaskAssignment.id)).where(
            TaskAssignment.task_id == task.id,
            TaskAssignment.status.not_in(["completed", "cancelled"]),
        )
    ):
        raise TaskStateConflictError
    now = utc_now()
    task.final_summary = payload.summary
    task.submitted_at = now
    task.status = "awaiting_acceptance"
    task.updated_at = now
    _add_activity(
        session,
        task_id=task.id,
        kind="final_submitted",
        actor_type="human",
        actor_human_id=user.id,
    )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action="task.final_submitted",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def decide_task_acceptance(
    session: Session,
    *,
    user: HumanUser,
    task_id: UUID,
    payload: TaskAcceptanceDecision,
    human_session_id: UUID | None,
    request_id: str,
) -> TaskDetail:
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    _require_owner(task, membership)
    if task.status != "awaiting_acceptance":
        raise TaskStateConflictError
    now = utc_now()
    if payload.decision == "accept":
        task.status = "completed"
        task.accepted_at = now
        task.completed_at = now
    else:
        task.status = "active"
        task.revision += 1
        task.final_summary = None
        task.submitted_at = None
    task.updated_at = now
    decision_activity = _add_activity(
        session,
        task_id=task.id,
        kind="accepted" if payload.decision == "accept" else "changes_requested",
        actor_type="human",
        actor_human_id=user.id,
        metadata={"note": payload.note} if payload.note else {},
    )
    if payload.decision == "request_changes":
        session.flush()
        participants = list(
            session.scalars(
                select(TaskAgentParticipant).where(
                    TaskAgentParticipant.task_id == task.id,
                    TaskAgentParticipant.active.is_(True),
                )
            )
        )
        for participant in participants:
            _queue_collaboration_assignment(
                session,
                task=task,
                human_id=participant.human_user_id,
                agent_id=participant.agent_id,
                created_by_human_id=user.id,
                assignment_kind="revision",
                trigger_activity_id=decision_activity.id,
                instruction=(
                    "Human 已要求修改任务结果。请读取完整任务上下文和历史结果，"
                    f"按以下意见完成新一轮修改：\n\n{payload.note}"
                ),
            )
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id,
        action=f"task.{payload.decision}",
        target_type="task",
        target_id=str(task.id),
        outcome="success",
        request_id=request_id,
    )
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)


def _digest_lease(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _agent_collaboration_context(
    session: Session, *, task_id: UUID
) -> tuple[list[UUID], list[AgentCollaborationUpdate]]:
    participant_ids = list(
        session.scalars(
            select(TaskAgentParticipant.agent_id)
            .where(
                TaskAgentParticipant.task_id == task_id,
                TaskAgentParticipant.active.is_(True),
            )
            .order_by(TaskAgentParticipant.selected_at)
        )
    )
    result_rows = list(
        session.scalars(
            select(TaskActivity)
            .where(
                TaskActivity.task_id == task_id,
                TaskActivity.activity_type == "assignment_result",
                TaskActivity.actor_agent_id.is_not(None),
            )
            .order_by(TaskActivity.created_at)
            .limit(100)
        )
    )
    updates = [
        AgentCollaborationUpdate(
            activity_id=item.id,
            agent_id=item.actor_agent_id,
            status=str(item.activity_metadata.get("status", "completed")),
            summary=str(item.activity_metadata.get("summary", "")),
            created_at=_as_utc(item.created_at),
        )
        for item in result_rows
        if item.actor_agent_id is not None
    ]
    return participant_ids, updates


def _requeue_expired_agent_runs(session: Session, *, agent: Agent, now: datetime) -> None:
    """Create one successor attempt for each expired lease without duplicating queued attempts."""
    expired = list(
        session.scalars(
            select(AgentRun).where(
                AgentRun.agent_id == agent.id,
                AgentRun.status.in_(["leased", "starting", "running"]),
                AgentRun.lease_expires_at < now,
            )
        )
    )
    for run in expired:
        run.status = "interrupted"
        assignment = session.get(TaskAssignment, run.assignment_id)
        if assignment is not None and assignment.status not in {"completed", "cancelled"}:
            queued_successor = session.scalar(
                select(AgentRun.id).where(
                    AgentRun.assignment_id == assignment.id,
                    AgentRun.agent_id == agent.id,
                    AgentRun.status == "queued",
                )
            )
            if queued_successor is None:
                session.add(
                    AgentRun(
                        assignment_id=assignment.id,
                        agent_id=agent.id,
                        attempt=run.attempt + 1,
                        checkpoint=run.checkpoint,
                    )
                )


def list_pending_agent_runs(
    session: Session,
    *,
    agent: Agent,
    task_id: UUID | None = None,
    limit: int = 50,
) -> AgentRunPendingList:
    now = utc_now()
    _requeue_expired_agent_runs(session, agent=agent, now=now)
    session.flush()
    statement = (
        select(AgentRun, TaskAssignment, Task)
        .join(TaskAssignment, TaskAssignment.id == AgentRun.assignment_id)
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.status == "queued",
            Task.status == "active",
        )
        .order_by(
            case(
                (TaskAssignment.priority == "urgent", 0),
                (TaskAssignment.priority == "high", 1),
                (TaskAssignment.priority == "normal", 2),
                else_=3,
            ),
            AgentRun.attempt.desc(),
            AgentRun.created_at,
        )
    )
    if task_id is not None:
        statement = statement.where(Task.id == task_id)
    rows = list(session.execute(statement.limit(limit)))
    session.commit()
    items = [
        AgentRunPending(
            run_id=run.id,
            task_id=task.id,
            thread_id=task.thread_id,
            task_title=task.title,
            assignment_id=assignment.id,
            source_activity_id=assignment.trigger_activity_id,
            source_message_id=assignment.source_message_id,
            instruction=assignment.instruction,
            target_human_user_id=assignment.responsible_human_user_id,
            target_agent_id=assignment.assignee_agent_id,
            reply_thread_id=task.thread_id,
            priority=assignment.priority,  # type: ignore[arg-type]
            attempt=run.attempt,
            checkpoint=run.checkpoint,
            created_at=_as_utc(run.created_at),
        )
        for run, assignment, task in rows
    ]
    return AgentRunPendingList(items=items, count=len(items))


def claim_agent_run(
    session: Session,
    *,
    agent: Agent,
    task_id: UUID | None = None,
    assignment_id: UUID | None = None,
) -> AgentRunClaim | None:
    now = utc_now()
    _requeue_expired_agent_runs(session, agent=agent, now=now)
    session.flush()
    statement = (
        select(AgentRun)
        .join(TaskAssignment, TaskAssignment.id == AgentRun.assignment_id)
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(
            AgentRun.agent_id == agent.id,
            AgentRun.status == "queued",
            Task.status == "active",
        )
        .order_by(
            case(
                (TaskAssignment.priority == "urgent", 0),
                (TaskAssignment.priority == "high", 1),
                (TaskAssignment.priority == "normal", 2),
                else_=3,
            ),
            AgentRun.attempt.desc(),
            AgentRun.created_at,
        )
    )
    if task_id is not None:
        statement = statement.where(TaskAssignment.task_id == task_id)
    if assignment_id is not None:
        statement = statement.where(TaskAssignment.id == assignment_id)
    run = session.scalar(statement.with_for_update(skip_locked=True).limit(1))
    if run is None:
        session.commit()
        return None
    assignment = session.get(TaskAssignment, run.assignment_id)
    if assignment is None:
        raise AgentRunNotFoundError
    task = session.get(Task, assignment.task_id)
    if task is None or task.status != "active":
        raise AgentRunNotFoundError
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(seconds=RUN_LEASE_SECONDS)
    run.status = "leased"
    run.lease_token_digest = _digest_lease(token)
    run.lease_expires_at = expires
    run.last_heartbeat_at = now
    run.claimed_at = now
    assignment.status = "running"
    assignment.updated_at = now
    _add_activity(
        session,
        task_id=task.id,
        kind="run_leased",
        actor_type="agent",
        actor_agent_id=agent.id,
        metadata={"assignment_id": str(assignment.id), "run_id": str(run.id)},
    )
    session.commit()
    participant_agent_ids, collaboration_updates = _agent_collaboration_context(
        session, task_id=task.id
    )
    return AgentRunClaim(
        status=run.status,
        run_id=run.id,
        lease_token=token,
        lease_expires_at=expires,
        task_id=task.id,
        thread_id=task.thread_id,
        task_title=task.title,
        task_goal=task.goal,
        assignment_id=assignment.id,
        source_activity_id=assignment.trigger_activity_id,
        source_message_id=assignment.source_message_id,
        target_human_user_id=assignment.responsible_human_user_id,
        target_agent_id=assignment.assignee_agent_id,
        reply_thread_id=task.thread_id,
        priority=assignment.priority,  # type: ignore[arg-type]
        instruction=assignment.instruction,
        expected_output=assignment.expected_output,
        due_at=_as_utc(assignment.due_at),
        attempt=run.attempt,
        checkpoint=run.checkpoint,
        participant_agent_ids=participant_agent_ids,
        collaboration_updates=collaboration_updates,
        wake_stage="claimed",
        local_session_id=run.local_session_id,
    )


def _leased_run(
    session: Session, *, agent: Agent, run_id: UUID, lease_token: str
) -> tuple[AgentRun, TaskAssignment, Task]:
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.agent_id == agent.id)
        .with_for_update()
    )
    now = utc_now()
    if (
        run is None
        or run.lease_token_digest is None
        or not secrets.compare_digest(run.lease_token_digest, _digest_lease(lease_token))
        or run.lease_expires_at is None
        or _as_utc(run.lease_expires_at) <= now
        or run.status not in {"leased", "starting", "running", "waiting_human"}
    ):
        raise AgentRunLeaseError
    assignment = session.get(TaskAssignment, run.assignment_id)
    task = session.get(Task, assignment.task_id) if assignment else None
    if assignment is None or task is None:
        raise AgentRunNotFoundError
    return run, assignment, task


def update_agent_run(
    session: Session, *, agent: Agent, run_id: UUID, payload: AgentRunUpdate
) -> AgentRunClaim:
    run, assignment, task = _leased_run(
        session, agent=agent, run_id=run_id, lease_token=payload.lease_token
    )
    now = utc_now()
    previous_status = run.status
    run.status = payload.status
    run.last_heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=RUN_LEASE_SECONDS)
    if "checkpoint" in payload.model_fields_set:
        run.checkpoint = payload.checkpoint
    if payload.local_session_id is not None:
        run.local_session_id = payload.local_session_id
    if payload.wake_status in {"mapped", "woken"} and run.session_mapped_at is None:
        run.session_mapped_at = now
    if payload.wake_status == "woken" and run.woken_at is None:
        run.woken_at = now
    if run.started_at is None and payload.status in {"starting", "running"}:
        run.started_at = now
    assignment.status = "waiting_human" if payload.status == "waiting_human" else "running"
    assignment.updated_at = now
    if payload.status != previous_status:
        _add_activity(
            session,
            task_id=task.id,
            kind="run_waiting_human" if payload.status == "waiting_human" else "run_progress",
            actor_type="agent",
            actor_agent_id=agent.id,
            metadata={
                "assignment_id": str(assignment.id),
                "run_id": str(run.id),
                "status": payload.status,
                "wake_status": payload.wake_status,
                "checkpoint": run.checkpoint,
            },
        )
    session.commit()
    participant_agent_ids, collaboration_updates = _agent_collaboration_context(
        session, task_id=task.id
    )
    return AgentRunClaim(
        status=run.status,
        run_id=run.id,
        lease_token=payload.lease_token,
        lease_expires_at=run.lease_expires_at,
        task_id=task.id,
        thread_id=task.thread_id,
        task_title=task.title,
        task_goal=task.goal,
        assignment_id=assignment.id,
        source_activity_id=assignment.trigger_activity_id,
        source_message_id=assignment.source_message_id,
        target_human_user_id=assignment.responsible_human_user_id,
        target_agent_id=assignment.assignee_agent_id,
        reply_thread_id=task.thread_id,
        priority=assignment.priority,  # type: ignore[arg-type]
        instruction=assignment.instruction,
        expected_output=assignment.expected_output,
        due_at=_as_utc(assignment.due_at),
        attempt=run.attempt,
        checkpoint=run.checkpoint,
        participant_agent_ids=participant_agent_ids,
        collaboration_updates=collaboration_updates,
        wake_stage=_run_wake_stage(run),  # type: ignore[arg-type]
        local_session_id=run.local_session_id,
    )


def _run_result_snapshot(session: Session, run: AgentRun, *, replayed: bool) -> dict:
    assignment = session.get(TaskAssignment, run.assignment_id)
    activity = session.scalar(
        select(TaskActivity).where(
            TaskActivity.task_id == assignment.task_id,
            TaskActivity.activity_type == "assignment_result",
            TaskActivity.activity_metadata["run_id"].as_string() == str(run.id),
        )
    )
    return {
        "run_id": str(run.id),
        "task_id": str(assignment.task_id),
        "assignment_id": str(run.assignment_id),
        "status": run.status,
        "wake_stage": _run_wake_stage(run),
        "checkpoint": run.checkpoint,
        "result_activity_id": str(activity.id) if activity else None,
        "replayed": replayed,
        "human_acceptance": "not_implied",
    }


def complete_agent_run(
    session: Session,
    *,
    agent: Agent,
    run_id: UUID,
    payload: AgentRunResult,
    idempotency_key: str | None = None,
) -> dict:
    hash_payload = payload.model_dump(mode="json")
    if "checkpoint" not in payload.model_fields_set:
        current_run = session.get(AgentRun, run_id)
        if current_run is not None and current_run.agent_id == agent.id:
            # Hash the effective preserved value, so retry is stable and an explicit
            # clear is not silently treated as the same result submission.
            hash_payload["checkpoint"] = current_run.checkpoint
    request_hash = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if idempotency_key is not None:
        existing_by_key = session.scalar(
            select(AgentRun).where(
                AgentRun.agent_id == agent.id,
                AgentRun.result_idempotency_key == idempotency_key,
            )
        )
        if existing_by_key is not None:
            if existing_by_key.id != run_id or existing_by_key.result_request_hash != request_hash:
                raise TaskStateConflictError
            if existing_by_key.status in {"completed", "partial", "failed", "cancelled"}:
                _task_participation_for_agent(
                    session,
                    agent=agent,
                    task_id=session.get(TaskAssignment, existing_by_key.assignment_id).task_id,
                )
                return _run_result_snapshot(session, existing_by_key, replayed=True)
    run, assignment, task = _leased_run(
        session, agent=agent, run_id=run_id, lease_token=payload.lease_token
    )
    now = utc_now()
    run.status = payload.status
    run.finished_at = now
    run.last_heartbeat_at = now
    run.lease_expires_at = None
    run.lease_token_digest = None
    if "checkpoint" in payload.model_fields_set:
        run.checkpoint = payload.checkpoint
    run.result_idempotency_key = idempotency_key
    run.result_request_hash = request_hash if idempotency_key is not None else None
    assignment.status = payload.status
    assignment.result_status = payload.status
    assignment.result_summary = payload.summary
    assignment.updated_at = now
    assignment.completed_at = now
    task.updated_at = now
    _add_activity(
        session,
        task_id=task.id,
        kind="assignment_result",
        actor_type="agent",
        actor_agent_id=agent.id,
        metadata={
            "assignment_id": str(assignment.id),
            "run_id": str(run.id),
            "status": payload.status,
            "summary": payload.summary,
        },
        external=True,
    )
    session.flush()
    # Results are already durable Task activities visible to every participant.
    # Creating a new Run for every other Agent causes mechanical acknowledgement loops;
    # review work must be requested explicitly through a Human-directed assignment.
    session.commit()
    return _run_result_snapshot(session, run, replayed=False)
