"""Add append-only Episode revision snapshots.

Revision ID: 20261024_0022
Revises: 20261024_0021
"""
from datetime import date, datetime
from typing import Any, Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0022"
down_revision: str | None = "20261024_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def upgrade() -> None:
    op.create_table(
        "episode_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("change_summary", sa.String(length=500)),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("revision_number > 0", name="ck_episode_revision_positive"),
        sa.UniqueConstraint("episode_id", "revision_number", name="uq_episode_revision_number"),
    )
    op.create_index("ix_episode_revisions_episode_id", "episode_revisions", ["episode_id"])

    bind = op.get_bind()
    revision_table = sa.table(
        "episode_revisions",
        sa.column("episode_id", sa.Integer()), sa.column("revision_number", sa.Integer()),
        sa.column("source", sa.String()), sa.column("change_summary", sa.String()),
        sa.column("snapshot", sa.JSON()),
    )
    episodes = bind.execute(sa.text("SELECT * FROM episodes")).mappings().all()
    for episode in episodes:
        episode_id = episode["id"]
        observations = [dict(row) for row in bind.execute(sa.text(
            "SELECT behavior_type, standardized_category, description, source_type, confidence, measured_value, unit, standardized_unit FROM observations WHERE episode_id = :id ORDER BY id"
        ), {"id": episode_id}).mappings()]
        interpretations = [row[0] for row in bind.execute(sa.text(
            "SELECT interpretation FROM owner_interpretations WHERE episode_id = :id ORDER BY id"
        ), {"id": episode_id})]
        safety = bind.execute(sa.text(
            "SELECT result, danger_signals, other_concern FROM safety_checks WHERE episode_id = :id"
        ), {"id": episode_id}).mappings().first()
        snapshot = {
            key: _json(episode[key]) for key in (
                "happened_at", "episode_type", "raw_owner_input", "context", "duration_seconds",
                "frequency_count", "intensity", "location", "trigger_context",
            )
        }
        snapshot["observations"] = [{key: _json(value) for key, value in row.items()} for row in observations]
        snapshot["owner_interpretations"] = interpretations
        snapshot["safety_check"] = None if safety is None else {key: _json(value) for key, value in safety.items()}
        bind.execute(revision_table.insert().values(
            episode_id=episode_id, revision_number=1, source="MIGRATED_BASELINE",
            change_summary=None, snapshot=snapshot,
        ))


def downgrade() -> None:
    op.drop_index("ix_episode_revisions_episode_id", table_name="episode_revisions")
    op.drop_table("episode_revisions")
