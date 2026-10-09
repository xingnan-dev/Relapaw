"""Add text understanding analysis aggregates.

Revision ID: 20261009_0005
Revises: 20261008_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261009_0005"
down_revision = "20261008_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("adapter_name", sa.String(100), nullable=False),
        sa.Column("model_provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_contract_version", sa.String(50), nullable=False),
        sa.Column("input_contract_version", sa.String(50), nullable=False),
        sa.Column("output_contract_version", sa.String(50), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("normalized_output", sa.JSON()),
        sa.Column("error_code", sa.String(100)),
        sa.Column("source_episode_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("episode_id", "request_id", name="uq_analysis_run_episode_request"),
        sa.CheckConstraint("status IN ('COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')", name="ck_analysis_run_status"),
    )
    op.create_index("ix_analysis_runs_episode_id", "analysis_runs", ["episode_id"])

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_type", sa.String(100), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence_label", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('PROPOSED', 'CONFIRMED', 'REJECTED')", name="ck_claim_status"),
        sa.CheckConstraint("confidence_label IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_claim_confidence"),
    )
    op.create_index("ix_claims_analysis_run_id", "claims", ["analysis_run_id"])

    op.create_table(
        "claim_evidence_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_reference_id", sa.Integer(), sa.ForeignKey("evidence_references.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer()),
        sa.Column("field_path", sa.String(200), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("excerpt", sa.Text()),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('SUPPORTS', 'LIMITS', 'CONTEXT')", name="ck_claim_evidence_role"),
    )
    op.create_index("ix_claim_evidence_references_claim_id", "claim_evidence_references", ["claim_id"])
    op.create_index("ix_claim_evidence_references_evidence_reference_id", "claim_evidence_references", ["evidence_reference_id"])

    op.create_table(
        "uncertainties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('MISSING_CONTEXT', 'ALTERNATIVE_EXPLANATION', 'LIMITED_OBSERVATION', 'OTHER')", name="ck_uncertainty_kind"),
    )
    op.create_index("ix_uncertainties_claim_id", "uncertainties", ["claim_id"])

    op.create_table(
        "user_confirmations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("claim_id", name="uq_user_confirmation_claim"),
        sa.CheckConstraint("decision IN ('CONFIRMED', 'REJECTED')", name="ck_confirmation_decision"),
    )
    op.create_index("ix_user_confirmations_claim_id", "user_confirmations", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_user_confirmations_claim_id", table_name="user_confirmations")
    op.drop_table("user_confirmations")
    op.drop_index("ix_uncertainties_claim_id", table_name="uncertainties")
    op.drop_table("uncertainties")
    op.drop_index("ix_claim_evidence_references_evidence_reference_id", table_name="claim_evidence_references")
    op.drop_index("ix_claim_evidence_references_claim_id", table_name="claim_evidence_references")
    op.drop_table("claim_evidence_references")
    op.drop_index("ix_claims_analysis_run_id", table_name="claims")
    op.drop_table("claims")
    op.drop_index("ix_analysis_runs_episode_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
