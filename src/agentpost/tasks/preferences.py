"""Human-only task preferences and voluntary membership revocation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentpost.control.models import HumanUser
from agentpost.identity.models import utc_now
from agentpost.tasks.models import (
    AgentRun,
    HumanTaskPreference,
    TaskActivity,
    TaskAgentParticipant,
    TaskAssignment,
)
from agentpost.tasks.schemas import TaskPreferenceUpdate


def preference_summary(session: Session, task_id: UUID, human_id: UUID) -> dict:
    pref = session.get(HumanTaskPreference, (human_id, task_id))
    seen = set(pref.seen_activity_ids if pref else [])
    messages = session.execute(
        select(TaskActivity.id, TaskActivity.actor_human_user_id).where(
            TaskActivity.task_id == task_id,
            TaskActivity.activity_type.in_(["task_message", "assignment_result"]),
        )
    ).all()
    return {
        "personal_state": pref.list_state if pref else "active",
        "unread_count": sum(str(id_) not in seen and actor != human_id for id_, actor in messages),
    }


def update_preference(
    session: Session, *, user: HumanUser, task_id: UUID, payload: TaskPreferenceUpdate
) -> dict:
    from agentpost.tasks.service import _task_context

    _task_context(session, task_id=task_id, user=user, lock=True)
    pref = session.get(HumanTaskPreference, (user.id, task_id))
    if pref is None:
        pref = HumanTaskPreference(human_user_id=user.id, task_id=task_id, seen_activity_ids=[])
        session.add(pref)
    if payload.list_state is not None:
        pref.list_state = payload.list_state
    # Only explicitly displayed snapshot IDs: concurrent or unseen messages stay unread.
    valid = (
        session.scalars(
            select(TaskActivity.id).where(
                TaskActivity.task_id == task_id, TaskActivity.id.in_(payload.seen_activity_ids)
            )
        ).all()
        if payload.seen_activity_ids
        else []
    )
    pref.seen_activity_ids = sorted(set(pref.seen_activity_ids) | {str(id_) for id_ in valid})
    session.commit()
    return preference_summary(session, task_id, user.id)


def leave_task(session: Session, *, user: HumanUser, task_id: UUID) -> None:
    from agentpost.tasks.service import TaskStateConflictError, _add_activity, _task_context

    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    if membership.role == "owner":
        raise TaskStateConflictError
    # Existing terminal membership state revokes access; activity records why it ended.
    membership.status = "declined"
    membership.updated_at = utc_now()
    for participant in session.scalars(
        select(TaskAgentParticipant).where(
            TaskAgentParticipant.task_id == task_id, TaskAgentParticipant.human_user_id == user.id
        )
    ):
        participant.active = False
    assignments = session.scalars(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.responsible_human_user_id == user.id,
            TaskAssignment.status.in_(["queued", "running", "waiting_human"]),
        )
    ).all()
    for assignment in assignments:
        assignment.status = "cancelled"
        assignment.cancellation_reason = "human_left_task"
        for run in session.scalars(
            select(AgentRun).where(
                AgentRun.assignment_id == assignment.id,
                AgentRun.status.in_(["queued", "leased", "starting", "running", "waiting_human"]),
            )
        ):
            run.status = "cancelled"
            run.cancellation_reason = "human_left_task"
            run.finished_at = utc_now()
            run.lease_token_digest = None
            run.lease_expires_at = None
    _add_activity(
        session,
        task_id=task_id,
        kind="member_left",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=user.id,
        metadata={"reason": "voluntary_exit"},
    )
    task.updated_at = utc_now()
    session.commit()
