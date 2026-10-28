"""Expand media evidence to concrete record types and revision history.

Revision ID: 20261024_0024
Revises: 20261024_0023
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0024"
down_revision: str | None = "20261024_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_attachments") as batch:
        batch.add_column(sa.Column("pet_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("life_event_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("relationship_event_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("captured_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("owner_caption", sa.Text()))
        batch.add_column(sa.Column("duration_seconds", sa.Integer()))
        batch.add_column(sa.Column("ai_candidate_observation", sa.Text()))
        batch.add_column(sa.Column("ai_candidate_status", sa.String(length=20), nullable=False, server_default="NONE"))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("UPDATE media_attachments SET pet_id = (SELECT pet_id FROM episodes WHERE episodes.id = media_attachments.episode_id), owner_caption = observable_facts")
    with op.batch_alter_table("media_attachments") as batch:
        batch.alter_column("pet_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("episode_id", existing_type=sa.Integer(), nullable=True)
        batch.create_foreign_key("fk_media_attachment_pet", "pets", ["pet_id"], ["id"], ondelete="CASCADE")
        batch.create_foreign_key("fk_media_attachment_life_event", "life_events", ["life_event_id"], ["id"], ondelete="CASCADE")
        batch.create_foreign_key("fk_media_attachment_relationship_event", "relationship_events", ["relationship_event_id"], ["id"], ondelete="CASCADE")
        batch.create_check_constraint("ck_media_ai_candidate_status", "ai_candidate_status IN ('NONE', 'PENDING', 'CONFIRMED', 'REJECTED', 'WITHDRAWN')")
        batch.create_check_constraint("ck_media_exactly_one_record", "(CASE WHEN episode_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN life_event_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN relationship_event_id IS NOT NULL THEN 1 ELSE 0 END) = 1")
        batch.create_check_constraint("ck_media_duration_positive", "duration_seconds IS NULL OR duration_seconds > 0")
        batch.create_index("ix_media_attachments_pet_id", ["pet_id"])
        batch.create_index("ix_media_attachments_life_event_id", ["life_event_id"])
        batch.create_index("ix_media_attachments_relationship_event_id", ["relationship_event_id"])
    op.create_table(
        "media_attachment_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("media_attachments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("owner_caption", sa.Text()),
        sa.Column("ai_candidate_observation", sa.Text()),
        sa.Column("ai_candidate_status", sa.String(length=20), nullable=False),
        sa.Column("change_summary", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("attachment_id", "revision_number", name="uq_media_attachment_revision_number"),
    )
    op.create_index("ix_media_attachment_revisions_attachment_id", "media_attachment_revisions", ["attachment_id"])
    op.execute("INSERT INTO media_attachment_revisions (attachment_id, revision_number, captured_at, owner_caption, ai_candidate_observation, ai_candidate_status, change_summary) SELECT id, 1, captured_at, owner_caption, ai_candidate_observation, ai_candidate_status, '迁移既有附件' FROM media_attachments")
    op.create_table(
        "memory_candidate_media_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("memory_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_attachment_id", sa.Integer(), sa.ForeignKey("media_attachments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("candidate_id", "media_attachment_id", name="uq_memory_candidate_media_reference"),
    )
    op.create_index("ix_memory_candidate_media_references_candidate_id", "memory_candidate_media_references", ["candidate_id"])
    op.create_index("ix_memory_candidate_media_references_media_attachment_id", "memory_candidate_media_references", ["media_attachment_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_candidate_media_references_media_attachment_id", table_name="memory_candidate_media_references")
    op.drop_index("ix_memory_candidate_media_references_candidate_id", table_name="memory_candidate_media_references")
    op.drop_table("memory_candidate_media_references")
    op.drop_index("ix_media_attachment_revisions_attachment_id", table_name="media_attachment_revisions")
    op.drop_table("media_attachment_revisions")
    with op.batch_alter_table("media_attachments") as batch:
        batch.drop_constraint("ck_media_duration_positive", type_="check")
        batch.drop_constraint("ck_media_exactly_one_record", type_="check")
        batch.drop_constraint("ck_media_ai_candidate_status", type_="check")
        batch.drop_constraint("fk_media_attachment_relationship_event", type_="foreignkey")
        batch.drop_constraint("fk_media_attachment_life_event", type_="foreignkey")
        batch.drop_constraint("fk_media_attachment_pet", type_="foreignkey")
        batch.drop_index("ix_media_attachments_relationship_event_id")
        batch.drop_index("ix_media_attachments_life_event_id")
        batch.drop_index("ix_media_attachments_pet_id")
        batch.alter_column("episode_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("updated_at")
        batch.drop_column("ai_candidate_status")
        batch.drop_column("ai_candidate_observation")
        batch.drop_column("duration_seconds")
        batch.drop_column("owner_caption")
        batch.drop_column("captured_at")
        batch.drop_column("relationship_event_id")
        batch.drop_column("life_event_id")
        batch.drop_column("pet_id")
