from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("datetime must include a timezone")
    return value.astimezone(UTC)


class AgentChoice(TaskModel):
    agent_ids: list[UUID] = Field(min_length=1, max_length=16)
    primary_agent_id: UUID

    @model_validator(mode="after")
    def validate_primary(self) -> AgentChoice:
        if len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("agent_ids must be unique")
        if self.primary_agent_id not in self.agent_ids:
            raise ValueError("primary_agent_id must be selected")
        return self


class TaskCreate(AgentChoice):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=10_000)
    expected_output: str = Field(min_length=1, max_length=10_000)
    due_at: datetime | None = None

    @field_validator("title", "goal", "expected_output")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def normalize_due_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class AgentTaskCreate(TaskModel):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=10_000)
    expected_output: str = Field(min_length=1, max_length=10_000)
    due_at: datetime | None = None

    @field_validator("title", "goal", "expected_output")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def normalize_due_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class TaskMembersInvite(TaskModel):
    human_user_ids: list[UUID] = Field(min_length=1, max_length=50)

    @field_validator("human_user_ids")
    @classmethod
    def unique_human_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("human_user_ids must be unique")
        return value


class TaskInvitationDecision(AgentChoice):
    pass


class TaskStatusUpdate(TaskModel):
    action: Literal["pause", "resume", "cancel", "archive", "restore"]
    reason: str | None = Field(default=None, max_length=2000)


class TaskAssignmentCreate(TaskModel):
    responsible_human_user_id: UUID
    assignee_agent_id: UUID
    instruction: str = Field(min_length=1, max_length=10_000)
    expected_output: str | None = Field(default=None, max_length=10_000)
    due_at: datetime | None = None

    @field_validator("instruction")
    @classmethod
    def clean_assignment_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("expected_output")
    @classmethod
    def clean_optional_expected_output(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("due_at")
    @classmethod
    def normalize_due_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value)


class TaskFinalSubmission(TaskModel):
    summary: str = Field(min_length=1, max_length=20_000)


class TaskAcceptanceDecision(TaskModel):
    decision: Literal["accept", "request_changes"]
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("note")
    @classmethod
    def clean_acceptance_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_change_request_note(self) -> TaskAcceptanceDecision:
        if self.decision == "request_changes" and self.note is None:
            raise ValueError("note is required when requesting changes")
        return self


class FriendRequestCreate(TaskModel):
    username: str = Field(min_length=3, max_length=32)


class FriendRequestDecision(TaskModel):
    decision: Literal["accept", "decline"]


class AgentSummary(TaskModel):
    agent_id: UUID
    display_name: str
    address: str
    capabilities: list[str]
    connection_state: str | None = None
    role: Literal["primary", "support"] | None = None


class FriendResponse(TaskModel):
    friendship_id: UUID | None = None
    human_user_id: UUID
    username: str
    display_name: str
    relation_status: Literal["pending_incoming", "pending_outgoing", "accepted", "suggested"]
    last_contact_at: datetime | None = None
    agents: list[AgentSummary] = Field(default_factory=list)


class TaskMember(TaskModel):
    human_user_id: UUID
    username: str
    display_name: str
    role: Literal["owner", "member"]
    status: Literal["invited", "active"]
    primary_agent_id: UUID | None
    agent_selection_source: Literal["selected", "default"]
    email_notification_status: Literal["not_applicable", "pending", "sent", "failed"]
    agents: list[AgentSummary]
    invited_at: datetime
    joined_at: datetime | None


class TaskAssignmentResponse(TaskModel):
    assignment_id: UUID
    responsible_human_user_id: UUID
    responsible_human_display_name: str
    assignee_agent_id: UUID
    assignee_agent_display_name: str
    assignment_kind: Literal["participant_start", "human_directed", "result_sync"]
    instruction: str
    expected_output: str
    due_at: datetime | None
    status: str
    result_status: str | None
    result_summary: str | None
    run_status: str | None
    created_at: datetime


class TaskActivityResponse(TaskModel):
    activity_id: UUID
    kind: str
    actor_type: Literal["human", "agent", "platform"]
    actor_display_name: str | None
    target_display_name: str | None
    metadata: dict[str, Any]
    security_label: Literal["platform_event", "external_agent_content"]
    created_at: datetime


class TaskSummary(TaskModel):
    task_id: UUID
    thread_id: UUID
    title: str
    goal: str
    expected_output: str
    status: str
    due_at: datetime | None
    revision: int
    owner_human_user_id: UUID
    owner_display_name: str
    coordinator_agent_id: UUID
    membership_role: Literal["owner", "member"]
    membership_status: Literal["invited", "active"]
    active_member_count: int
    invited_member_count: int
    assignment_count: int
    pending_assignment_count: int
    final_summary: str | None
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskSummary):
    members: list[TaskMember]
    assignments: list[TaskAssignmentResponse]
    activities: list[TaskActivityResponse]


class AgentCollaborationUpdate(TaskModel):
    activity_id: UUID
    agent_id: UUID
    status: str
    summary: str
    created_at: datetime


class AgentRunClaim(TaskModel):
    run_id: UUID
    lease_token: str
    lease_expires_at: datetime
    task_id: UUID
    thread_id: UUID
    task_title: str
    task_goal: str
    assignment_id: UUID
    instruction: str
    expected_output: str
    due_at: datetime | None
    attempt: int
    participant_agent_ids: list[UUID]
    collaboration_updates: list[AgentCollaborationUpdate]
    security_label: Literal["external_agent_content"] = "external_agent_content"


class AgentRunUpdate(TaskModel):
    lease_token: str = Field(min_length=20, max_length=500)
    status: Literal["starting", "running", "waiting_human"]
    checkpoint: dict[str, Any] = Field(default_factory=dict)


class AgentRunResult(TaskModel):
    lease_token: str = Field(min_length=20, max_length=500)
    status: Literal["completed", "partial", "failed", "cancelled"]
    summary: str = Field(min_length=1, max_length=20_000)
    checkpoint: dict[str, Any] = Field(default_factory=dict)
