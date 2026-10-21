"""Allow user-authored long-term memory candidates without AI.

Revision ID: 20261020_0012
Revises: 20261020_0011
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0012"
down_revision: str | None = "20261020_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("memory_candidates") as batch:
        batch.add_column(sa.Column("source_type", sa.String(20), nullable=False, server_default="CLAIM"))
        batch.alter_column("claim_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("source_episode_updated_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.create_check_constraint("ck_memory_candidate_source_type", "source_type IN ('CLAIM', 'MANUAL')")
        batch.create_check_constraint(
            "ck_memory_candidate_source_fields",
            "(source_type = 'CLAIM' AND claim_id IS NOT NULL AND source_episode_updated_at IS NOT NULL) OR "
            "(source_type = 'MANUAL' AND claim_id IS NULL AND source_episode_updated_at IS NULL)",
        )


def downgrade() -> None:
    op.execute("DELETE FROM memory_candidates WHERE source_type = 'MANUAL'")
    with op.batch_alter_table("memory_candidates") as batch:
        batch.drop_constraint("ck_memory_candidate_source_fields", type_="check")
        batch.drop_constraint("ck_memory_candidate_source_type", type_="check")
        batch.alter_column("source_episode_updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column("claim_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("source_type")
