"""Phase 1 complete manual records.

Revision ID: 20261008_0002
Revises: 20261007_0001
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261008_0002"
down_revision: str | None = "20261007_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.add_column(sa.Column("duration_seconds", sa.Integer()))
        batch_op.add_column(sa.Column("frequency_count", sa.Integer()))
        batch_op.add_column(sa.Column("intensity", sa.Integer()))
        batch_op.add_column(sa.Column("location", sa.String(200)))
        batch_op.add_column(sa.Column("trigger_context", sa.Text()))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    with op.batch_alter_table("observations") as batch_op:
        batch_op.add_column(sa.Column("measured_value", sa.Float()))
        batch_op.add_column(sa.Column("unit", sa.String(50)))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    with op.batch_alter_table("owner_interpretations") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    op.create_table(
        "safety_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("danger_signals", sa.JSON(), nullable=False),
        sa.Column("other_concern", sa.Text()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "evidence_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer()),
        sa.Column("field_path", sa.String(200), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evidence_references_episode_id", "evidence_references", ["episode_id"])
    op.create_table(
        "episode_plan_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("observation_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("episode_id", "plan_id", name="uq_episode_plan_link"),
    )
    op.create_index("ix_episode_plan_links_episode_id", "episode_plan_links", ["episode_id"])
    op.create_index("ix_episode_plan_links_plan_id", "episode_plan_links", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_episode_plan_links_plan_id", table_name="episode_plan_links")
    op.drop_index("ix_episode_plan_links_episode_id", table_name="episode_plan_links")
    op.drop_table("episode_plan_links")
    op.drop_index("ix_evidence_references_episode_id", table_name="evidence_references")
    op.drop_table("evidence_references")
    op.drop_table("safety_checks")

    with op.batch_alter_table("owner_interpretations") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
    with op.batch_alter_table("observations") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("unit")
        batch_op.drop_column("measured_value")
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("trigger_context")
        batch_op.drop_column("location")
        batch_op.drop_column("intensity")
        batch_op.drop_column("frequency_count")
        batch_op.drop_column("duration_seconds")
