"""Track email verification separately from analyst approval."""
from alembic import op
import sqlalchemy as sa

revision = "20261120_reg_approval"
down_revision = "20261117_push_prefs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("approval_pending", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Preserve existing active/manual accounts. Recover pending public signups.
    op.execute("""UPDATE users SET email_verified = false
        WHERE is_active = false AND id IN
        (SELECT user_id FROM auth_otps WHERE purpose = 'EMAIL_VERIFICATION')
        AND id NOT IN (SELECT user_id FROM auth_otps
          WHERE purpose = 'EMAIL_VERIFICATION' AND verified_at IS NOT NULL)""")
    op.execute("""UPDATE users SET approval_pending = true WHERE is_active = false
        AND role_id IN (SELECT id FROM roles WHERE name = 'SOC_ANALYST')
        AND id IN (SELECT user_id FROM auth_otps WHERE purpose = 'EMAIL_VERIFICATION')""")


def downgrade():
    op.drop_column("users", "approval_pending")
    op.drop_column("users", "email_verified")
