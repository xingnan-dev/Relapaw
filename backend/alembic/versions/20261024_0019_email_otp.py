"""Add persistent, hashed email OTP challenges and rate-limit events.

Revision ID: 20261024_0019
Revises: 20261021_0018
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261024_0019"
down_revision: str | None = "20261021_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_otp_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("subject", "source_hash", "expires_at", "consumed_at", "invalidated_at", "created_at"):
        op.create_index(f"ix_email_otp_challenges_{column}", "email_otp_challenges", [column])
    op.create_table(
        "email_otp_rate_limit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("subject_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('REQUEST', 'VERIFY')", name="ck_email_otp_rate_action"),
    )
    for column in ("action", "subject_hash", "source_hash", "created_at"):
        op.create_index(f"ix_email_otp_rate_limit_events_{column}", "email_otp_rate_limit_events", [column])


def downgrade() -> None:
    op.drop_table("email_otp_rate_limit_events")
    op.drop_table("email_otp_challenges")
