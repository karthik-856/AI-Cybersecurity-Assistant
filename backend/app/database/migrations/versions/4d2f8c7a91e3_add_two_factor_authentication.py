"""add two factor authentication setting

Revision ID: 4d2f8c7a91e3
Revises: 237c0704690b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d2f8c7a91e3"
down_revision: Union[str, Sequence[str], None] = "237c0704690b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add two-factor authentication setting to users."""

    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Existing users receive False during migration.
    # Remove the database-level default afterward so future writes
    # are controlled by the application model.
    op.alter_column(
        "users",
        "two_factor_enabled",
        server_default=None,
    )


def downgrade() -> None:
    """Remove two-factor authentication setting."""

    op.drop_column(
        "users",
        "two_factor_enabled",
    )
