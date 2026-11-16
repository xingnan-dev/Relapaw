"""Add versioned controlled-knowledge assistant guidance runs.

Revision ID: 20261025_0025
Revises: 20261024_0024
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261025_0025"
down_revision: str | None = "20261024_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_guidance_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("adapter_name", sa.String(100), nullable=False),
        sa.Column("model_provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_contract_version", sa.String(80), nullable=False),
        sa.Column("input_contract_version", sa.String(50), nullable=False),
        sa.Column("output_contract_version", sa.String(50), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("knowledge_snapshot", sa.JSON(), nullable=False),
        sa.Column("normalized_output", sa.JSON()),
        sa.Column("error_code", sa.String(100)),
        sa.Column("source_episode_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("episode_id", "request_id", name="uq_guidance_run_episode_request"),
        sa.CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')", name="ck_guidance_run_status"),
        sa.CheckConstraint("mode IN ('RECORD_REVIEW', 'RECENT_CHANGE_COMPARISON', 'VET_TIMELINE')", name="ck_guidance_run_mode"),
    )
    op.create_index("ix_assistant_guidance_runs_episode_id", "assistant_guidance_runs", ["episode_id"])


def downgrade() -> None:
    op.drop_index("ix_assistant_guidance_runs_episode_id", table_name="assistant_guidance_runs")
    op.drop_table("assistant_guidance_runs")
