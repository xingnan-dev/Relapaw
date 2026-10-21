"""Add privacy lifecycle and immutable audit storage.

Revision ID: 20261020_0011
Revises: 20261020_0010
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0011"
down_revision: str | None = "20261020_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("deletion_due_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_users_deletion_due_at", ["deletion_due_at"])
    with op.batch_alter_table("episodes") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_episodes_deleted_at", ["deleted_at"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_pseudonym", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_pseudonym", sa.String(64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_pseudonym", "audit_events", ["actor_pseudonym"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_pseudonym", table_name="audit_events")
    op.drop_table("audit_events")
    with op.batch_alter_table("episodes") as batch:
        batch.drop_index("ix_episodes_deleted_at")
        batch.drop_column("deleted_at")
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_deletion_due_at")
        batch.drop_column("deletion_due_at")
