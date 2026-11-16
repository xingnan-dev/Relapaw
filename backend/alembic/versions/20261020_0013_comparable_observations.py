"""Add optional controlled comparison fields without replacing owner wording.

Revision ID: 20261020_0013
Revises: 20261020_0012
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0013"
down_revision: str | None = "20261020_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("observations") as batch:
        batch.add_column(sa.Column("standardized_category", sa.String(30)))
        batch.add_column(sa.Column("standardized_unit", sa.String(30)))
        batch.create_index("ix_observations_standardized_category", ["standardized_category"])


def downgrade() -> None:
    with op.batch_alter_table("observations") as batch:
        batch.drop_index("ix_observations_standardized_category")
        batch.drop_column("standardized_unit")
        batch.drop_column("standardized_category")
