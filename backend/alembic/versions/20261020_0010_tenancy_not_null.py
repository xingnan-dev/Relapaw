"""Require ownership after the explicit legacy assignment step.

Revision ID: 20261020_0010
Revises: 20261020_0009
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0010"
down_revision: str | None = "20261020_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    legacy_pets = connection.scalar(sa.text("SELECT count(*) FROM pets WHERE owner_user_id IS NULL"))
    legacy_profiles = connection.scalar(sa.text("SELECT count(*) FROM owner_profiles WHERE user_id IS NULL"))
    if legacy_pets or legacy_profiles:
        raise RuntimeError(
            "Legacy rows have no owner; run `python -m app.demo.assign_legacy_owner "
            "--allow-legacy-demo-data` at revision 20261020_0009 before retrying"
        )
    with op.batch_alter_table("pets") as batch:
        batch.alter_column("owner_user_id", existing_type=sa.String(36), nullable=False)
    with op.batch_alter_table("owner_profiles") as batch:
        batch.alter_column("user_id", existing_type=sa.String(36), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("owner_profiles") as batch:
        batch.alter_column("user_id", existing_type=sa.String(36), nullable=True)
    with op.batch_alter_table("pets") as batch:
        batch.alter_column("owner_user_id", existing_type=sa.String(36), nullable=True)
