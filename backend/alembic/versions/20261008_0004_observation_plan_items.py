"""Add normalized observation plan items.

Revision ID: 20261008_0004
Revises: 20261008_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0004"
down_revision = "20261008_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observation_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("observation_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "sort_order", name="uq_plan_item_sort_order"),
    )
    op.create_index("ix_observation_plan_items_plan_id", "observation_plan_items", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_observation_plan_items_plan_id", table_name="observation_plan_items")
    op.drop_table("observation_plan_items")
