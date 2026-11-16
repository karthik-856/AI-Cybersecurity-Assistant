"""create analyst actions table

Revision ID: 7e8f9a0b1c2d
Revises: 1c2e32ce8992
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e8f9a0b1c2d"
down_revision: Union[str, None] = "1c2e32ce8992"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyst_actions",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "action_id",
            sa.String(length=60),
            nullable=False,
        ),
        sa.Column(
            "analyst_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "incident_id",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "investigation_id",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "action_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analyst_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.incident_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.investigation_id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("action_id"),
    )

    op.create_index(
        "ix_analyst_actions_id",
        "analyst_actions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_action_id",
        "analyst_actions",
        ["action_id"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_analyst_id",
        "analyst_actions",
        ["analyst_id"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_incident_id",
        "analyst_actions",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_investigation_id",
        "analyst_actions",
        ["investigation_id"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_action_type",
        "analyst_actions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        "ix_analyst_actions_created_at",
        "analyst_actions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analyst_actions_created_at",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_action_type",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_investigation_id",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_incident_id",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_analyst_id",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_action_id",
        table_name="analyst_actions",
    )
    op.drop_index(
        "ix_analyst_actions_id",
        table_name="analyst_actions",
    )
    op.drop_table("analyst_actions")
