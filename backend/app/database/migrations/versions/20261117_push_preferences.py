"""Store device notification preferences with each subscription."""
from alembic import op
import sqlalchemy as sa

revision = "20261117_push_prefs"
down_revision = "20261116_auth_limits"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("critical_alerts", "high_alerts", "notification_preview"):
        op.add_column("push_subscriptions", sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    for name in ("notification_preview", "high_alerts", "critical_alerts"):
        op.drop_column("push_subscriptions", name)
