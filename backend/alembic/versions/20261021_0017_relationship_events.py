"""Add layered owner-pet and pet-pet relationship events.

Revision ID: 20261021_0017
Revises: 20261021_0016
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261021_0017"
down_revision: str | None = "20261021_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relationship_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_kind", sa.String(length=20), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_type", sa.String(length=30), nullable=False),
        sa.Column("observation_text", sa.Text(), nullable=False),
        sa.Column("source_episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("relationship_kind IN ('OWNER_PET', 'PET_PET')", name="ck_relationship_event_kind"),
        sa.CheckConstraint("observation_type IN ('OWNER_INTERACTION', 'SHARED_REST', 'INTERACTION', 'AVOIDANCE', 'CONFLICT', 'RESOURCE_SHARING', 'OTHER')", name="ck_relationship_observation_type"),
    )
    op.create_index("ix_relationship_events_owner_user_id", "relationship_events", ["owner_user_id"])
    op.create_index("ix_relationship_events_happened_at", "relationship_events", ["happened_at"])
    op.create_index("ix_relationship_events_source_episode_id", "relationship_events", ["source_episode_id"])
    op.create_table(
        "relationship_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("relationship_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("event_id", "pet_id", name="uq_relationship_participant"),
    )
    op.create_index("ix_relationship_participants_event_id", "relationship_participants", ["event_id"])
    op.create_index("ix_relationship_participants_pet_id", "relationship_participants", ["pet_id"])
    op.create_table(
        "relationship_interpretations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("relationship_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_relationship_interpretations_event_id", "relationship_interpretations", ["event_id"])
    op.create_table(
        "relationship_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("relationship_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("relationship_kind", sa.String(length=20), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_pet_ids", sa.JSON(), nullable=False),
        sa.Column("observation_type", sa.String(length=30), nullable=False),
        sa.Column("observation_text", sa.Text(), nullable=False),
        sa.Column("owner_interpretation", sa.Text()),
        sa.Column("source_episode_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "revision_number", name="uq_relationship_revision_number"),
    )
    op.create_index("ix_relationship_revisions_event_id", "relationship_revisions", ["event_id"])


def downgrade() -> None:
    op.drop_table("relationship_revisions")
    op.drop_table("relationship_interpretations")
    op.drop_table("relationship_participants")
    op.drop_table("relationship_events")
