"""Persist authentication request budgets across workers and restarts."""
from alembic import op
import sqlalchemy as sa

revision = "20261116_auth_limits"
down_revision = "6160a7aa00dd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("auth_rate_limits", sa.Column("scope", sa.String(128), primary_key=True), sa.Column("window_started_at", sa.DateTime(), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False))
    op.create_index("ix_auth_rate_limits_window_started_at", "auth_rate_limits", ["window_started_at"])


def downgrade():
    op.drop_table("auth_rate_limits")
