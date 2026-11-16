"""Persist account onboarding completion.

Revision ID: 20261024_0020
Revises: 20261024_0019
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0020"
down_revision: str | None = "20261024_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
