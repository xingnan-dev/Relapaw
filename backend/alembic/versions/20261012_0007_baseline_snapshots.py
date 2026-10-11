"""Add deterministic quantitative baseline snapshots.

Revision ID: 20261012_0007
Revises: 20261011_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0007"
down_revision = "20261011_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "baseline_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("window", sa.String(10), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True)),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("algorithm_version", sa.String(100), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "pet_id", "window", "as_of", "algorithm_version", "source_fingerprint",
            name="uq_baseline_snapshot_identity",
        ),
        sa.CheckConstraint("window IN ('7d', '30d', '90d', 'all')", name="ck_baseline_snapshot_window"),
        sa.CheckConstraint(
            "status IN ('READY', 'INSUFFICIENT_DATA', 'EMPTY')",
            name="ck_baseline_snapshot_status",
        ),
    )
    op.create_index("ix_baseline_snapshots_pet_id", "baseline_snapshots", ["pet_id"])


def downgrade() -> None:
    op.drop_index("ix_baseline_snapshots_pet_id", table_name="baseline_snapshots")
    op.drop_table("baseline_snapshots")
