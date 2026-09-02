from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentpost.db import Base
from agentpost.identity.models import utc_now


class Friendship(Base):
    """A Human-confirmed relationship; message history is only a suggestion source."""

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("human_a_id", "human_b_id", name="uq_friendships_human_pair"),
        CheckConstraint("human_a_id <> human_b_id", name="ck_friendships_distinct_humans"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'removed')",
            name="ck_friendships_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    human_a_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="CASCADE"), nullable=False
    )
    human_b_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_human_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint(
            "coordinator_agent_id",
            "agent_creation_key",
            name="uq_tasks_agent_creation_key",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'awaiting_acceptance', 'completed', "
            "'cancelled', 'archived')",
            name="ck_tasks_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    owner_human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("human_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    coordinator_agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    thread_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, unique=True, index=True, default=uuid4
    )
    agent_creation_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    memberships: Mapped[list[TaskMembership]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    agent_participants: Mapped[list[TaskAgentParticipant]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    activities: Mapped[list[TaskActivity]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    assignments: Mapped[list[TaskAssignment]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )


class TaskMembership(Base):
    __tablename__ = "task_memberships"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'member')", name="ck_task_memberships_role"),
        CheckConstraint(
            "status IN ('invited', 'active', 'declined')", name="ck_task_memberships_status"
        ),
        CheckConstraint(
            "agent_selection_source IN ('selected', 'default')",
            name="ck_task_memberships_agent_selection_source",
        ),
        CheckConstraint(
            "email_notification_status IN ('not_applicable', 'pending', 'sent', 'failed')",
            name="ck_task_memberships_email_notification_status",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("human_users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    primary_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True
    )
    agent_selection_source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="selected"
    )
    email_notification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="not_applicable"
    )
    email_notification_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    invited_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    task: Mapped[Task] = relationship(back_populates="memberships")


class TaskAgentParticipant(Base):
    __tablename__ = "task_agent_participants"
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'support')", name="ck_task_agents_role"),
    )

    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), primary_key=True
    )
    human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    task: Mapped[Task] = relationship(back_populates="agent_participants")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        UniqueConstraint(
            "assignee_agent_id",
            "trigger_activity_id",
            name="uq_task_assignments_agent_trigger",
        ),
        CheckConstraint(
            "assignment_kind IN ('participant_start', 'human_directed', 'result_sync')",
            name="ck_task_assignments_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'waiting_human', 'completed', "
            "'partial', 'failed', 'cancelled')",
            name="ck_task_assignments_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    responsible_human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="RESTRICT"), nullable=False
    )
    assignment_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default="human_directed"
    )
    trigger_activity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("task_activities.id", ondelete="CASCADE"),
        nullable=True,
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task: Mapped[Task] = relationship(back_populates="assignments")
    runs: Mapped[list[AgentRun]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", passive_deletes=True
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("assignment_id", "attempt", name="uq_agent_runs_assignment_attempt"),
        CheckConstraint(
            "status IN ('queued', 'leased', 'starting', 'running', 'waiting_human', "
            "'completed', 'partial', 'failed', 'cancelled', 'interrupted')",
            name="ck_agent_runs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("task_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    lease_token_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    assignment: Mapped[TaskAssignment] = relationship(back_populates="runs")


class TaskActivity(Base):
    __tablename__ = "task_activities"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_human_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="SET NULL"), nullable=True
    )
    actor_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    target_human_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="SET NULL"), nullable=True
    )
    activity_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    security_label: Mapped[str] = mapped_column(
        String(32), nullable=False, default="platform_event"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    task: Mapped[Task] = relationship(back_populates="activities")
