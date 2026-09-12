"""Opt-in public first contact, bounded guest proof and registration claim."""

import sqlalchemy as sa
from alembic import op

revision = "0044_guest_contacts"
down_revision = "0043_webhook_protocol"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contact_preferences",
        sa.Column(
            "human_id",
            sa.Uuid(),
            sa.ForeignKey("human_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "contact_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), sa.ForeignKey("human_users.id"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("human_users.id")),
        sa.Column("sender_name", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id"), unique=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('pending', 'accepted', 'declined')", name="ck_contact_decision"
        ),
    )
    op.create_index("ix_contact_requests_recipient_id", "contact_requests", ["recipient_id"])
    op.create_index("ix_contact_requests_sender_id", "contact_requests", ["sender_id"])


def downgrade():
    op.drop_table("contact_requests")
    op.drop_table("contact_preferences")
