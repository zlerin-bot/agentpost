"""Per-Task publication order independent of event timestamps."""

import sqlalchemy as sa
from alembic import op

revision = "0039_task_activity_sequence"
down_revision = "0038_human_task_preferences"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_activities", sa.Column("sequence", sa.BigInteger(), nullable=True))
    op.execute(
        sa.text("""
        UPDATE task_activities SET sequence = ranked.seq FROM (
            SELECT id, row_number() OVER (PARTITION BY task_id ORDER BY created_at, id) AS seq
            FROM task_activities
        ) AS ranked WHERE task_activities.id = ranked.id
    """)
    )
    with op.batch_alter_table("task_activities") as batch:
        batch.alter_column("sequence", existing_type=sa.BigInteger(), nullable=False)
        batch.create_unique_constraint("uq_task_activities_sequence", ["task_id", "sequence"])


def downgrade():
    with op.batch_alter_table("task_activities") as batch:
        batch.drop_constraint("uq_task_activities_sequence", type_="unique")
        batch.drop_column("sequence")
