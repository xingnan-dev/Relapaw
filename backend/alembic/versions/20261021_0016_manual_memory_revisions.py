"""Add append-only revisions for user-authored memories.

Revision ID: 20261021_0016
Revises: 20261021_0015
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261021_0016"
down_revision: str | None = "20261021_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("memory_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("candidate_id", "revision_number", name="uq_memory_revision_number"),
    )
    op.create_index("ix_memory_revisions_candidate_id", "memory_revisions", ["candidate_id"])
    connection = op.get_bind()
    candidates = connection.execute(sa.text(
        "SELECT id, claim_snapshot FROM memory_candidates WHERE source_type = 'MANUAL' ORDER BY id"
    )).fetchall()
    import json
    for candidate_id, raw_snapshot in candidates:
        snapshot = json.loads(raw_snapshot) if isinstance(raw_snapshot, str) else raw_snapshot
        connection.execute(sa.text(
            "INSERT INTO memory_revisions (candidate_id, revision_number, category, statement) VALUES (:candidate_id, 1, :category, :statement)"
        ), {"candidate_id": candidate_id, "category": snapshot.get("claim_type", "OTHER"), "statement": snapshot.get("statement", "")})


def downgrade() -> None:
    op.drop_index("ix_memory_revisions_candidate_id", table_name="memory_revisions")
    op.drop_table("memory_revisions")
