"""create auth sessions table

Revision ID: 9c7e6a5b4d3f
Revises: 4d2f8c7a91e3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c7e6a5b4d3f"
down_revision: Union[str, Sequence[str], None] = "4d2f8c7a91e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the server-side authentication sessions table."""

    op.create_table(
        "auth_sessions",
        sa.Column(
            "session_id",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_index(
        "ix_auth_sessions_session_id",
        "auth_sessions",
        ["session_id"],
        unique=False,
    )

    op.create_index(
        "ix_auth_sessions_user_id",
        "auth_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_auth_sessions_expires_at",
        "auth_sessions",
        ["expires_at"],
        unique=False,
    )

    op.create_index(
        "ix_auth_sessions_revoked_at",
        "auth_sessions",
        ["revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the server-side authentication sessions table."""

    op.drop_index(
        "ix_auth_sessions_revoked_at",
        table_name="auth_sessions",
    )

    op.drop_index(
        "ix_auth_sessions_expires_at",
        table_name="auth_sessions",
    )

    op.drop_index(
        "ix_auth_sessions_user_id",
        table_name="auth_sessions",
    )

    op.drop_index(
        "ix_auth_sessions_session_id",
        table_name="auth_sessions",
    )

    op.drop_table("auth_sessions")