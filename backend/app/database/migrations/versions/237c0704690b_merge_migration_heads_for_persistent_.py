"""merge migration heads for persistent web push

Revision ID: 237c0704690b
Revises: 6fd25bb6ace0, 8b7f4a91c2d1
Create Date: 2026-09-14 13:41:24.732688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '237c0704690b'
down_revision: Union[str, Sequence[str], None] = ('6fd25bb6ace0', '8b7f4a91c2d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
