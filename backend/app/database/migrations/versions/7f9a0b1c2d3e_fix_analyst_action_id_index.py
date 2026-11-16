"""fix analyst action id unique index

Revision ID: 7f9a0b1c2d3e
Revises: 7e8f9a0b1c2d
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7f9a0b1c2d3e"
down_revision: Union[str, None] = "7e8f9a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "analyst_actions_action_id_key",
        "analyst_actions",
        type_="unique",
    )

    op.drop_index(
        "ix_analyst_actions_action_id",
        table_name="analyst_actions",
    )

    op.create_index(
        "ix_analyst_actions_action_id",
        "analyst_actions",
        ["action_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analyst_actions_action_id",
        table_name="analyst_actions",
    )

    op.create_index(
        "ix_analyst_actions_action_id",
        "analyst_actions",
        ["action_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "analyst_actions_action_id_key",
        "analyst_actions",
        ["action_id"],
    )