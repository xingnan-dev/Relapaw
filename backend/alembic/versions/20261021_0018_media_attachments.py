"""Add local episode media attachments.

Revision ID: 20261021_0018
Revises: 20261021_0017
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261021_0018"
down_revision: str | None = "20261021_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("media_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="AVAILABLE"),
        sa.Column("observable_facts", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('AVAILABLE', 'MISSING', 'CORRUPT')", name="ck_media_attachment_status"),
    )
    op.create_index("ix_media_attachments_episode_id", "media_attachments", ["episode_id"])

def downgrade() -> None:
    op.drop_table("media_attachments")
