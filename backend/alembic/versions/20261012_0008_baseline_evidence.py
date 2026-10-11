"""Add field-level baseline evidence lineage.

Revision ID: 20261012_0008
Revises: 20261012_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0008"
down_revision = "20261012_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "baseline_evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("baseline_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="SET NULL")),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("observations.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("window_segment", sa.String(20), nullable=False),
        sa.Column("metric_key", sa.String(300), nullable=False),
        sa.Column("field_path", sa.String(200), nullable=False),
        sa.Column("value_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_type IN ('EPISODE', 'OBSERVATION')", name="ck_baseline_evidence_source_type"),
        sa.CheckConstraint("window_segment IN ('CURRENT', 'COMPARISON')", name="ck_baseline_evidence_segment"),
    )
    op.create_index("ix_baseline_evidences_snapshot_id", "baseline_evidences", ["snapshot_id"])
    op.create_index("ix_baseline_evidences_episode_id", "baseline_evidences", ["episode_id"])
    op.create_index("ix_baseline_evidences_observation_id", "baseline_evidences", ["observation_id"])


def downgrade() -> None:
    op.drop_index("ix_baseline_evidences_observation_id", table_name="baseline_evidences")
    op.drop_index("ix_baseline_evidences_episode_id", table_name="baseline_evidences")
    op.drop_index("ix_baseline_evidences_snapshot_id", table_name="baseline_evidences")
    op.drop_table("baseline_evidences")
