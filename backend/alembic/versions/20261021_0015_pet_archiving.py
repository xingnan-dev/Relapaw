"""Add reversible pet archiving.

Revision ID: 20261021_0015
Revises: 20261020_0014
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261021_0015"
down_revision: str | None = "20261020_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pets") as batch:
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_pets_archived_at", ["archived_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("pets") as batch:
        batch.drop_index("ix_pets_archived_at")
        batch.drop_column("archived_at")
