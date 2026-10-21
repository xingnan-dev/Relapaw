"""Allow durable RUNNING analysis idempotency reservations.

Revision ID: 20261020_0014
Revises: 20261020_0013
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0014"
down_revision: str | None = "20261020_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_runs") as batch:
        batch.drop_constraint("ck_analysis_run_status", type_="check")
        batch.create_check_constraint(
            "ck_analysis_run_status",
            "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')",
        )


def downgrade() -> None:
    op.execute("DELETE FROM analysis_runs WHERE status = 'RUNNING'")
    with op.batch_alter_table("analysis_runs") as batch:
        batch.drop_constraint("ck_analysis_run_status", type_="check")
        batch.create_check_constraint(
            "ck_analysis_run_status",
            "status IN ('COMPLETED', 'FAILED', 'BLOCKED_BY_SAFETY')",
        )
