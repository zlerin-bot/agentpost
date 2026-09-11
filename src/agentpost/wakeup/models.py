from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from agentpost.db import Base
from agentpost.identity.models import utc_now


class AgentWakeChannel(Base):
    __tablename__ = "agent_wake_channels"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_wake_channels_agent"),
        CheckConstraint(
            "channel_type IN ('feishu_aily_webhook', 'feishu_notification_webhook')",
            name="ck_agent_wake_channels_type",
        ),
        CheckConstraint(
            "status IN ('configured', 'active', 'error', 'disabled')",
            name="ck_agent_wake_channels_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    human_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("human_users.id", ondelete="CASCADE"), nullable=False
    )
    connector_instance_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("connector_instances.id", ondelete="CASCADE"),
        nullable=True,
    )
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    encrypted_endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_bearer_token: Mapped[str] = mapped_column(Text, nullable=False)
    auth_scheme: Mapped[str] = mapped_column(String(20), nullable=False, default="bearer")
    last_dispatch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="configured")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class AgentWakeDelivery(Base):
    __tablename__ = "agent_wake_deliveries"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_agent_wake_deliveries_run"),
        CheckConstraint(
            "status IN ('pending', 'sending', 'delivered', 'failed', 'cancelled')",
            name="ck_agent_wake_deliveries_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_wake_channels.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
