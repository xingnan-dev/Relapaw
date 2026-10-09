"""Add episode follow-up lifecycle.

Revision ID: 20261008_0003
Revises: 20261008_0002
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261008_0003"
down_revision: str | None = "20261008_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "episode_follow_ups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("result_episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="RESTRICT"), unique=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("outcome", sa.String(30)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("result_episode_id IS NULL OR source_episode_id != result_episode_id", name="ck_follow_up_distinct_episodes"),
        sa.CheckConstraint(
            "(status = 'PENDING' AND result_episode_id IS NULL AND outcome IS NULL AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND result_episode_id IS NOT NULL AND outcome IS NOT NULL AND completed_at IS NOT NULL) OR "
            "(status = 'CANCELLED' AND result_episode_id IS NULL AND outcome IS NULL AND completed_at IS NULL)",
            name="ck_follow_up_state_fields",
        ),
    )
    op.create_index("ix_episode_follow_ups_source_episode_id", "episode_follow_ups", ["source_episode_id"])
    op.create_index("ix_episode_follow_ups_result_episode_id", "episode_follow_ups", ["result_episode_id"], unique=True)
    op.create_index("ix_episode_follow_ups_scheduled_at", "episode_follow_ups", ["scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_episode_follow_ups_scheduled_at", table_name="episode_follow_ups")
    op.drop_index("ix_episode_follow_ups_result_episode_id", table_name="episode_follow_ups")
    op.drop_index("ix_episode_follow_ups_source_episode_id", table_name="episode_follow_ups")
    op.drop_table("episode_follow_ups")
