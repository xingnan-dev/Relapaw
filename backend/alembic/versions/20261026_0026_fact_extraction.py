"""Classify historical interpretations and new fact-extraction candidates.

Revision ID: 20261026_0026
Revises: 20261025_0025
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261026_0026"
down_revision: str | None = "20261025_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("claims") as batch:
        batch.add_column(sa.Column(
            "candidate_kind", sa.String(40), nullable=False,
            server_default="LEGACY_INTERPRETATION",
        ))
        batch.create_check_constraint(
            "ck_claim_candidate_kind",
            "candidate_kind IN ('LEGACY_INTERPRETATION', 'OBSERVATION', 'OWNER_INTERPRETATION')",
        )


def downgrade() -> None:
    with op.batch_alter_table("claims") as batch:
        batch.drop_constraint("ck_claim_candidate_kind", type_="check")
        batch.drop_column("candidate_kind")
