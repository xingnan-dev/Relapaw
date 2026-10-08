"""Initial Relapaw Phase 0.1 schema.

Revision ID: 20261007_0001
Revises: None
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261007_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owner_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_preference", sa.Text()),
        sa.Column("observation_preference", sa.Text()),
        sa.Column("response_preference", sa.Text()),
        sa.Column("explanation_preference", sa.Text()),
    )
    op.create_table(
        "pets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("species", sa.String(50), nullable=False),
        sa.Column("breed", sa.String(100)),
        sa.Column("birth_date", sa.Date()),
        sa.Column("approximate_age", sa.String(100)),
        sa.Column("sex", sa.String(30)),
        sa.Column("neutered", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "pet_baselines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("social_behavior", sa.JSON()),
        sa.Column("activity_pattern", sa.JSON()),
        sa.Column("feeding_pattern", sa.JSON()),
        sa.Column("resting_pattern", sa.JSON()),
        sa.Column("handling_preference", sa.JSON()),
        sa.Column("hiding_pattern", sa.JSON()),
    )
    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("episode_type", sa.String(100), nullable=False),
        sa.Column("raw_owner_input", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_episodes_pet_id", "episodes", ["pet_id"])
    op.create_index("ix_episodes_happened_at", "episodes", ["happened_at"])
    op.create_table(
        "life_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_index("ix_life_events_pet_id", "life_events", ["pet_id"])
    op.create_table(
        "observation_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("items_to_observe", sa.JSON(), nullable=False),
    )
    op.create_index("ix_observation_plans_pet_id", "observation_plans", ["pet_id"])
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("behavior_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float()),
    )
    op.create_index("ix_observations_episode_id", "observations", ["episode_id"])
    op.create_table(
        "owner_interpretations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
    )
    op.create_index("ix_owner_interpretations_episode_id", "owner_interpretations", ["episode_id"])
    op.create_table(
        "veterinary_escalations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("vet_brief", sa.Text()),
    )
    op.create_index("ix_veterinary_escalations_episode_id", "veterinary_escalations", ["episode_id"])


def downgrade() -> None:
    op.drop_index("ix_veterinary_escalations_episode_id", table_name="veterinary_escalations")
    op.drop_table("veterinary_escalations")
    op.drop_index("ix_owner_interpretations_episode_id", table_name="owner_interpretations")
    op.drop_table("owner_interpretations")
    op.drop_index("ix_observations_episode_id", table_name="observations")
    op.drop_table("observations")
    op.drop_index("ix_observation_plans_pet_id", table_name="observation_plans")
    op.drop_table("observation_plans")
    op.drop_index("ix_life_events_pet_id", table_name="life_events")
    op.drop_table("life_events")
    op.drop_index("ix_episodes_happened_at", table_name="episodes")
    op.drop_index("ix_episodes_pet_id", table_name="episodes")
    op.drop_table("episodes")
    op.drop_table("pet_baselines")
    op.drop_table("pets")
    op.drop_table("owner_profiles")
