"""Explicit Human recovery of existing work, invalidating all older leases."""

from sqlalchemy import select, update

from agentpost.identity.models import utc_now
from agentpost.tasks.models import (
    AgentRun,
    Task,
    TaskActivity,
    TaskAgentParticipant,
    TaskAssignment,
)
from agentpost.tasks.service import (
    TaskNotFoundError,
    TaskStateConflictError,
    _add_activity,
    _human_agent,
    _task_context,
    _task_detail,
)


def continue_work(session, *, user, task_id, assignment_id, payload):
    task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
    session.execute(update(Task).where(Task.id == task_id).values(updated_at=Task.updated_at))
    assignment = session.scalar(
        select(TaskAssignment)
        .where(TaskAssignment.id == assignment_id, TaskAssignment.task_id == task_id)
        .with_for_update()
    )
    if (
        not assignment
        or membership.status != "active"
        or user.id not in (task.owner_human_user_id, assignment.responsible_human_user_id)
    ):
        raise TaskNotFoundError
    previous = session.scalar(
        select(TaskActivity).where(
            TaskActivity.task_id == task_id,
            TaskActivity.actor_human_user_id == user.id,
            TaskActivity.activity_type == "human_work_continued",
            TaskActivity.idempotency_key == str(payload.operation_id),
        )
    )
    if previous:
        if previous.activity_metadata.get("request") != payload.model_dump(mode="json"):
            raise TaskStateConflictError
        return _task_detail(session, task=task, viewer_membership=membership)
    if task.status != "active" or assignment.status in ("completed", "cancelled"):
        raise TaskStateConflictError
    target = None
    if payload.action == "reassign":
        # Same responsible Human, already participating owned Agent only.
        target = _human_agent(session, assignment.responsible_human_user_id, payload.agent_id)
        participant = (
            session.get(TaskAgentParticipant, (task_id, payload.agent_id))
            if payload.agent_id
            else None
        )
        if (
            not target
            or not participant
            or not participant.active
            or participant.human_user_id != assignment.responsible_human_user_id
        ):
            raise TaskNotFoundError
    runs = list(
        session.scalars(
            select(AgentRun)
            .where(AgentRun.assignment_id == assignment_id)
            .order_by(AgentRun.attempt)
            .with_for_update()
        )
    )
    now = utc_now()
    for run in runs:
        if run.status in ("queued", "leased", "starting", "running", "waiting_human"):
            run.status = "cancelled"
            run.cancellation_reason = "human_continued"
            run.lease_token_digest = None
            run.lease_expires_at = None
            run.finished_at = now
    old_agent = assignment.assignee_agent_id
    if target:
        assignment.assignee_agent_id = target.id
        assignment.status = "queued"
        run = AgentRun(
            assignment_id=assignment_id,
            agent_id=target.id,
            attempt=max((r.attempt for r in runs), default=0) + 1,
            checkpoint={
                "human_continuation": payload.body,
                "previous_checkpoint": runs[-1].checkpoint if runs else {},
            },
        )
        session.add(run)
        session.flush()
        from agentpost.wakeup.service import enqueue_run_wake

        enqueue_run_wake(
            session, agent_id=target.id, task_id=task_id, assignment_id=assignment_id, run_id=run.id
        )
    else:
        assignment.status = "completed"
        assignment.result_status = None
        assignment.cancellation_reason = "human_completed"
        assignment.result_summary = payload.body
        assignment.completed_at = now
    assignment.updated_at = now
    task.updated_at = now
    _add_activity(
        session,
        task_id=task_id,
        kind="human_work_continued",
        actor_type="human",
        actor_human_id=user.id,
        target_human_id=assignment.responsible_human_user_id,
        external=True,
        idempotency_key=str(payload.operation_id),
        metadata={
            "assignment_id": str(assignment_id),
            "action": payload.action,
            "summary": payload.body,
            "previous_agent_id": str(old_agent),
            "request": payload.model_dump(mode="json"),
        },
    )
    task.updated_at = now
    session.commit()
    return _task_detail(session, task=task, viewer_membership=membership)
