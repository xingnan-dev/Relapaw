"""Add evidence-backed interaction pattern candidates.

Revision ID: 20261024_0023
Revises: 20261024_0022
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0023"
down_revision: str | None = "20261024_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interaction_pattern_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_kind", sa.String(length=20), nullable=False),
        sa.Column("participant_pet_ids", sa.JSON(), nullable=False),
        sa.Column("initial_self_report", sa.Text()),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("observable_pattern", sa.Text(), nullable=False),
        sa.Column("counterevidence_summary", sa.Text(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("coverage_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generator_version", sa.String(length=100), nullable=False),
        sa.Column("confidence_limit", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ELIGIBLE"),
        sa.Column("memory_status", sa.String(length=20), nullable=False, server_default="NOT_INCLUDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("relationship_kind IN ('OWNER_PET', 'PET_PET')", name="ck_interaction_pattern_kind"),
        sa.CheckConstraint("status IN ('ELIGIBLE', 'CONFIRMED', 'REJECTED', 'WITHDRAWN')", name="ck_interaction_pattern_status"),
        sa.CheckConstraint("memory_status IN ('NOT_INCLUDED', 'INCLUDED', 'WITHDRAWN')", name="ck_interaction_pattern_memory_status"),
        sa.CheckConstraint("evidence_count >= 3", name="ck_interaction_pattern_evidence_count"),
    )
    op.create_index("ix_interaction_pattern_candidates_owner_user_id", "interaction_pattern_candidates", ["owner_user_id"])
    op.create_table(
        "interaction_pattern_evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("interaction_pattern_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_event_id", sa.Integer(), sa.ForeignKey("relationship_events.id", ondelete="SET NULL")),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("observation_type", sa.String(length=30), nullable=False),
        sa.Column("observation_snapshot", sa.Text(), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('SUPPORTS', 'CONTRADICTS')", name="ck_interaction_pattern_evidence_role"),
        sa.UniqueConstraint("candidate_id", "relationship_event_id", name="uq_interaction_pattern_event"),
    )
    op.create_index("ix_interaction_pattern_evidences_candidate_id", "interaction_pattern_evidences", ["candidate_id"])
    op.create_index("ix_interaction_pattern_evidences_relationship_event_id", "interaction_pattern_evidences", ["relationship_event_id"])
    op.create_table(
        "interaction_pattern_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("interaction_pattern_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("observable_pattern", sa.Text(), nullable=False),
        sa.Column("counterevidence_summary", sa.Text(), nullable=False),
        sa.Column("confidence_limit", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("candidate_id", "revision_number", name="uq_interaction_pattern_revision_number"),
    )
    op.create_index("ix_interaction_pattern_revisions_candidate_id", "interaction_pattern_revisions", ["candidate_id"])
    op.create_table(
        "interaction_pattern_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("interaction_pattern_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("resulting_status", sa.String(length=20), nullable=False),
        sa.Column("previous_memory_status", sa.String(length=20), nullable=False),
        sa.Column("resulting_memory_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('CONFIRM', 'REJECT', 'WITHDRAW', 'INCLUDE_IN_MEMORY', 'WITHDRAW_FROM_MEMORY')", name="ck_interaction_pattern_decision_action"),
    )
    op.create_index("ix_interaction_pattern_decisions_candidate_id", "interaction_pattern_decisions", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_interaction_pattern_decisions_candidate_id", table_name="interaction_pattern_decisions")
    op.drop_table("interaction_pattern_decisions")
    op.drop_index("ix_interaction_pattern_revisions_candidate_id", table_name="interaction_pattern_revisions")
    op.drop_table("interaction_pattern_revisions")
    op.drop_index("ix_interaction_pattern_evidences_relationship_event_id", table_name="interaction_pattern_evidences")
    op.drop_index("ix_interaction_pattern_evidences_candidate_id", table_name="interaction_pattern_evidences")
    op.drop_table("interaction_pattern_evidences")
    op.drop_index("ix_interaction_pattern_candidates_owner_user_id", table_name="interaction_pattern_candidates")
    op.drop_table("interaction_pattern_candidates")
