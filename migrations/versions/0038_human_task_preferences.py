"""Personal task list and Human message views, independent of Agent state."""

import sqlalchemy as sa
from alembic import op

revision = "0038_human_task_preferences"
down_revision = "0037_task_activity_relations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "human_task_preferences",
        sa.Column(
            "human_user_id",
            sa.Uuid(),
            sa.ForeignKey("human_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("list_state", sa.String(16), nullable=False),
        sa.Column("seen_activity_ids", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("human_task_preferences")
