"""Add long-term memory candidates and decisions.

Revision ID: 20261011_0006
Revises: 20261009_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20261011_0006"
down_revision = "20261009_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_snapshot", sa.JSON(), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("uncertainty_snapshot", sa.JSON(), nullable=False),
        sa.Column("model_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_episode_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("claim_id", name="uq_memory_candidates_claim_id"),
    )
    op.create_index("ix_memory_candidates_pet_id", "memory_candidates", ["pet_id"])
    op.create_index("ix_memory_candidates_claim_id", "memory_candidates", ["claim_id"])

    op.create_table(
        "memory_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("memory_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("candidate_id", "request_id", name="uq_memory_decision_candidate_request"),
        sa.CheckConstraint("decision IN ('INCLUDE', 'WITHDRAW')", name="ck_memory_decision_type"),
    )
    op.create_index("ix_memory_decisions_candidate_id", "memory_decisions", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_decisions_candidate_id", table_name="memory_decisions")
    op.drop_table("memory_decisions")
    op.drop_index("ix_memory_candidates_claim_id", table_name="memory_candidates")
    op.drop_index("ix_memory_candidates_pet_id", table_name="memory_candidates")
    op.drop_table("memory_candidates")
