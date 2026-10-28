"""Add optional caregiver background, dynamic pet profile, and pet avatars.

Revision ID: 20261024_0021
Revises: 20261024_0020
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0021"
down_revision: str | None = "20261024_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for name, column_type in (
        ("weight_kg", sa.Float()), ("known_conditions", sa.JSON()), ("medications", sa.JSON()),
        ("allergies", sa.JSON()), ("living_environment", sa.Text()),
        ("veterinarian_confirmed_facts", sa.JSON()), ("owner_observations", sa.JSON()),
    ):
        op.add_column("pets", sa.Column(name, column_type))
    for name, column_type in (
        ("living_together_since", sa.Date()), ("primary_caregiver", sa.String(length=200)),
        ("household_members", sa.JSON()), ("daily_routine", sa.Text()), ("pet_alone_hours", sa.Float()),
        ("pet_care_experience", sa.Text()), ("current_concerns", sa.Text()),
        ("reminder_preference", sa.String(length=100)), ("recording_capacity", sa.Text()),
        ("household_context", sa.JSON()), ("caregiving_constraints", sa.Text()),
        ("ai_context_fields", sa.JSON()), ("ai_context_consent_updated_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("owner_profiles", sa.Column(name, column_type))
    op.add_column("owner_profiles", sa.Column("ai_context_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "pet_avatars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("pet_id", name="uq_pet_avatar_pet_id"),
    )
    op.create_index("ix_pet_avatars_pet_id", "pet_avatars", ["pet_id"])


def downgrade() -> None:
    op.drop_index("ix_pet_avatars_pet_id", table_name="pet_avatars")
    op.drop_table("pet_avatars")
    for name in (
        "ai_context_consent_updated_at", "ai_context_fields", "ai_context_enabled", "caregiving_constraints",
        "household_context", "recording_capacity", "reminder_preference", "current_concerns", "pet_care_experience",
        "pet_alone_hours", "daily_routine", "household_members", "primary_caregiver", "living_together_since",
    ):
        op.drop_column("owner_profiles", name)
    for name in (
        "owner_observations", "veterinarian_confirmed_facts", "living_environment", "allergies",
        "medications", "known_conditions", "weight_kg",
    ):
        op.drop_column("pets", name)
