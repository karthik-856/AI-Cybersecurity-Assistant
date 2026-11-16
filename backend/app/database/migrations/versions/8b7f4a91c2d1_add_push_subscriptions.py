"""add persistent web push subscriptions

Revision ID: 8b7f4a91c2d1
Revises: 1c2e32ce8992
Create Date: 2026-09-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8b7f4a91c2d1"
down_revision: Union[str, Sequence[str], None] = "1c2e32ce8992"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )

    op.create_index(
        "ix_push_subscriptions_id",
        "push_subscriptions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_push_subscriptions_user_id",
        "push_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_push_subscriptions_created_at",
        "push_subscriptions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_push_subscriptions_created_at",
        table_name="push_subscriptions",
    )
    op.drop_index(
        "ix_push_subscriptions_user_id",
        table_name="push_subscriptions",
    )
    op.drop_index(
        "ix_push_subscriptions_id",
        table_name="push_subscriptions",
    )
    op.drop_table("push_subscriptions")
