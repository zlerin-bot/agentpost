from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from agentpost.db import Base
from agentpost.identity.models import utc_now


class ContactPreference(Base):
    __tablename__ = "contact_preferences"
    human_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("human_users.id", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    introduction: Mapped[str] = mapped_column(String(280), default="")


class ContactRequest(Base):
    """Single immutable introduction, never a parallel conversation or task ACL."""

    __tablename__ = "contact_requests"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('pending', 'accepted', 'declined')", name="ck_contact_decision"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    payload_digest: Mapped[str] = mapped_column(String(64))
    recipient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("human_users.id"), index=True)
    sender_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("human_users.id"), index=True)
    sender_name: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(20), default="greeting")
    reply_body: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    reported: Mapped[bool] = mapped_column(Boolean, default=False)
    decision: Mapped[str] = mapped_column(String(16), default="pending")
    task_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("tasks.id"), unique=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
