"""Separate greetings from explicitly accepted collaboration."""

import sqlalchemy as sa
from alembic import op

revision = "0045_contact_intent"
down_revision = "0044_guest_contacts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contact_preferences",
        sa.Column("introduction", sa.String(280), nullable=False, server_default=""),
    )
    op.add_column(
        "contact_requests",
        sa.Column("intent", sa.String(20), nullable=False, server_default="greeting"),
    )
    op.add_column("contact_requests", sa.Column("reply_body", sa.Text(), nullable=True))
    op.add_column(
        "contact_requests", sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "contact_requests",
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "contact_requests",
        sa.Column("reported", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    for name in ("reported", "blocked", "replied_at", "reply_body", "intent"):
        op.drop_column("contact_requests", name)
    op.drop_column("contact_preferences", "introduction")
