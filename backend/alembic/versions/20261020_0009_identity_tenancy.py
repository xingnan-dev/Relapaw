"""Add identity, server sessions, consent records, and tenant roots.

Revision ID: 20261020_0009
Revises: 20261012_0008
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0009"
down_revision: str | None = "20261012_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('ACTIVE', 'PENDING_DELETION', 'DISABLED')", name="ck_user_status"),
    )
    op.create_table(
        "user_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "subject", name="uq_user_identity_provider_subject"),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
    op.create_table(
        "identity_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("accepted_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("provider", "subject", name="uq_identity_invitation_provider_subject"),
        sa.CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'REVOKED')", name="ck_identity_invitation_status"),
    )
    op.create_index("ix_identity_invitations_accepted_user_id", "identity_invitations", ["accepted_user_id"])
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent_summary", sa.String(200)),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"])
    op.create_table(
        "terms_acceptances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("terms_version", sa.String(100), nullable=False),
        sa.Column("privacy_version", sa.String(100), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.UniqueConstraint("user_id", "terms_version", "privacy_version", name="uq_terms_acceptance_versions"),
        sa.CheckConstraint("source IN ('ONBOARDING', 'VERSION_UPDATE')", name="ck_terms_acceptance_source"),
    )
    op.create_index("ix_terms_acceptances_user_id", "terms_acceptances", ["user_id"])

    with op.batch_alter_table("pets") as batch:
        batch.add_column(sa.Column("owner_user_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_pets_owner_user_id_users", "users", ["owner_user_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_pets_owner_user_id", ["owner_user_id"])
    with op.batch_alter_table("owner_profiles") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_owner_profiles_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE")
        batch.create_unique_constraint("uq_owner_profiles_user_id", ["user_id"])

def downgrade() -> None:
    with op.batch_alter_table("owner_profiles") as batch:
        batch.drop_constraint("uq_owner_profiles_user_id", type_="unique")
        batch.drop_constraint("fk_owner_profiles_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
    with op.batch_alter_table("pets") as batch:
        batch.drop_index("ix_pets_owner_user_id")
        batch.drop_constraint("fk_pets_owner_user_id_users", type_="foreignkey")
        batch.drop_column("owner_user_id")
    op.drop_index("ix_terms_acceptances_user_id", table_name="terms_acceptances")
    op.drop_table("terms_acceptances")
    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_identity_invitations_accepted_user_id", table_name="identity_invitations")
    op.drop_table("identity_invitations")
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_table("users")
