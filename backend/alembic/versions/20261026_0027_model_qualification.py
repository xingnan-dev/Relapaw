"""Register the audited Qwen v7/guidance-v4 qualification.

Revision ID: 20261026_0027
Revises: 20261026_0026
"""
from datetime import datetime, timezone
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261026_0027"
down_revision: str | None = "20261026_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUALIFICATION_ID = "qwen-beijing-20261026-v7-guidance-v4"


def upgrade() -> None:
    table = op.create_table(
        "model_qualifications",
        sa.Column("qualification_id", sa.String(100), primary_key=True),
        sa.Column("manifest_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("endpoint_policy", sa.JSON(), nullable=False),
        sa.Column("contracts", sa.JSON(), nullable=False),
        sa.Column("knowledge_set_version", sa.String(100), nullable=False),
        sa.Column("evidence_manifest", sa.JSON(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('APPROVED', 'REVOKED')", name="ck_model_qualification_status"),
    )
    op.bulk_insert(table, [{
        "qualification_id": QUALIFICATION_ID,
        "manifest_version": "model-qualification/v1",
        "status": "APPROVED",
        "provider": "qwen",
        "model": "qwen3.7-plus-2026-05-26",
        "endpoint_policy": {"scheme": "https", "hostname_suffix": ".cn-beijing.maas.aliyuncs.com", "path": "/compatible-mode/v1"},
        "contracts": [
            {"purpose": "text_understanding", "prompt": "text-understanding/v7-verbatim-fact-extraction", "input": "understanding-input/v1", "output": "understanding-output/v2"},
            {"purpose": "assistant_guidance", "prompt": "assistant-guidance/v4-versioned-claim-citations", "input": "assistant-guidance-input/v1", "output": "assistant-guidance-output/v4"},
        ],
        "knowledge_set_version": "controlled-education/2026-10-25-v1",
        "evidence_manifest": [
            {"path": "evals/qwen_beijing_qualification_run_20261026_v3.json", "sha256": "6cba6958f2923419f3eb9b510de59a9c9b8860963de79fbd171d7308613484fd"},
            {"path": "evals/qwen_beijing_qualification_run_20261026_v4.json", "sha256": "2168f3afeb6675184806fd14c288df80a94ca22e77645656ee6212cffaa71831"},
        ],
        "approved_at": datetime(2026, 10, 26, tzinfo=timezone.utc),
        "revoked_at": None,
        "revocation_reason": None,
    }])


def downgrade() -> None:
    op.drop_table("model_qualifications")
