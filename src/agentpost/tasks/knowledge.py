"""Permission-scoped, source-backed context export; no inferred user profile."""

from datetime import UTC

from sqlalchemy import or_, select, update

from agentpost.control.models import HumanUser
from agentpost.identity.models import utc_now
from agentpost.tasks.models import Task, TaskActivity

KINDS = (
    "task_message",
    "assignment_result",
    "final_submitted",
    "accepted",
    "changes_requested",
    "human_work_continued",
    "assignment_created",
)


def context_snapshot(session, detail, query="", before=None, limit=30):
    # Caller must obtain detail through the current Human/Agent task authorization.
    statement = select(TaskActivity).where(
        TaskActivity.task_id == detail.task_id, TaskActivity.activity_type.in_(KINDS)
    )
    if before:
        anchor = session.get(TaskActivity, before)
        if not anchor or anchor.task_id != detail.task_id:
            from agentpost.tasks.service import TaskNotFoundError

            raise TaskNotFoundError
        statement = statement.where(TaskActivity.sequence < anchor.sequence)
    if query:
        statement = statement.where(
            or_(
                *(
                    TaskActivity.activity_metadata[field]
                    .as_string()
                    .contains(query, autoescape=True)
                    for field in ("body", "subject", "summary", "note", "instruction")
                )
            )
        )
    rows = list(session.scalars(statement.order_by(TaskActivity.sequence.desc()).limit(limit + 1)))
    sources = []
    for row in rows[:limit]:
        payload = row.activity_metadata or {}
        text = str(
            payload.get("body")
            or payload.get("summary")
            or payload.get("note")
            or payload.get("instruction")
            or ""
        )
        author = (
            session.get(HumanUser, row.actor_human_user_id) if row.actor_human_user_id else None
        )
        sources.append(
            {
                "activity_id": str(row.id),
                "author": author.display_name if author else "任务记录",
                "kind": row.activity_type,
                "human_id": str(row.actor_human_user_id) if row.actor_human_user_id else None,
                "created_at": row.created_at.replace(tzinfo=UTC).isoformat(),
                "subject": str(payload.get("subject") or ""),
                "excerpt": text[:2000],
                "truncated": len(text) > 2000,
                "source_url": (
                    f"/orbit?module=projects&view=board&task={detail.task_id}"
                    f"#task-activity-{row.id}"
                ),
            }
        )
    return {
        "task_id": str(detail.task_id),
        "title": detail.title,
        "goal": detail.goal,
        "expected_output": detail.expected_output,
        "status": detail.status,
        "generated_at": utc_now().isoformat(),
        "security_label": "external_agent_content",
        "summary_kind": "source_index_not_inferred_decisions",
        "summary": current_summary(session, detail.task_id),
        "confirmed_summary": current_summary(session, detail.task_id, confirmed_only=True),
        "sources": sources,
        "query": query,
        "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
        "work": [
            {
                "assignment_id": str(x.assignment_id),
                "responsible_human": x.responsible_human_display_name,
                "status": x.status,
                "instruction": x.instruction[:1000],
            }
            for x in detail.assignments
            if x.assignment_kind == "human_directed"
        ],
        "guidance": (
            "引用原始活动核实结论；讨论、Agent结果与Human验收是不同事实。"
            "复杂成果可用Markdown/HTML附件；普通交流无需强制格式或标签。"
        ),
    }


def publish_summary(session, *, task_id, user=None, agent=None, payload):
    from agentpost.tasks.service import (
        TaskNotFoundError,
        TaskOwnerRequiredError,
        _add_activity,
        _task_context,
        _task_participation_for_agent,
    )

    if agent:
        task, _, membership = _task_participation_for_agent(session, agent=agent, task_id=task_id)
        if payload.confirmed:
            raise TaskOwnerRequiredError
        human_id = membership.human_user_id
    else:
        task, membership = _task_context(session, task_id=task_id, user=user, lock=True)
        if membership.status != "active":
            raise TaskNotFoundError
        if payload.confirmed and membership.role != "owner":
            raise TaskOwnerRequiredError
        human_id = user.id
    session.execute(update(Task).where(Task.id == task_id).values(updated_at=Task.updated_at))
    ids = set(payload.source_activity_ids)
    records = list(
        session.scalars(
            select(TaskActivity).where(TaskActivity.task_id == task_id, TaskActivity.id.in_(ids))
        )
    )
    if len(records) != len(ids):
        raise TaskNotFoundError
    baseline = session.get(TaskActivity, payload.based_on_activity_id)
    if not baseline or baseline.task_id != task_id:
        raise TaskNotFoundError
    activity = _add_activity(
        session,
        task_id=task_id,
        kind="context_summary",
        actor_type="agent" if agent else "human",
        actor_human_id=human_id,
        actor_agent_id=agent.id if agent else None,
        external=True,
        metadata={**payload.model_dump(mode="json"), "based_on_sequence": baseline.sequence},
    )
    task.updated_at = utc_now()
    session.commit()
    return {"activity_id": str(activity.id), "confirmed": payload.confirmed}


def current_summary(session, task_id, confirmed_only=False):
    statement = (
        select(TaskActivity)
        .where(TaskActivity.task_id == task_id, TaskActivity.activity_type == "context_summary")
        .order_by(TaskActivity.sequence.desc())
    )
    if confirmed_only:
        statement = statement.where(
            TaskActivity.activity_metadata["confirmed"].as_boolean().is_(True)
        )
    row = session.scalar(statement.limit(1))
    if not row:
        return None
    latest = (
        session.scalar(
            select(TaskActivity.sequence)
            .where(TaskActivity.task_id == task_id, TaskActivity.activity_type.in_(KINDS))
            .order_by(TaskActivity.sequence.desc())
            .limit(1)
        )
        or 0
    )
    return {
        "activity_id": str(row.id),
        "actor_type": row.actor_type,
        **row.activity_metadata,
        "stale": latest > row.activity_metadata.get("based_on_sequence", 0),
    }
