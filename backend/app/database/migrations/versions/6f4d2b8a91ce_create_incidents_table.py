"""create incidents table

Revision ID: 6f4d2b8a91ce
Revises: 14a9c3f4ba5e
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f4d2b8a91ce"
down_revision: Union[str, Sequence[str], None] = "14a9c3f4ba5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incidents",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "incident_id",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "alert_id",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "severity",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "priority",
            sa.String(length=10),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="OPEN",
        ),

        sa.Column(
            "assigned_to_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "escalation_level",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "escalation_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "resolution_summary",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "resolved_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "closed_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.alert_id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["assigned_to_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("incident_id"),
    )

    op.create_index(
        "ix_incidents_id",
        "incidents",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_incident_id",
        "incidents",
        ["incident_id"],
        unique=True,
    )

    op.create_index(
        "ix_incidents_alert_id",
        "incidents",
        ["alert_id"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_severity",
        "incidents",
        ["severity"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_priority",
        "incidents",
        ["priority"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_status",
        "incidents",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_assigned_to_id",
        "incidents",
        ["assigned_to_id"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_resolved_at",
        "incidents",
        ["resolved_at"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_closed_at",
        "incidents",
        ["closed_at"],
        unique=False,
    )

    op.create_index(
        "ix_incidents_created_at",
        "incidents",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incidents_created_at",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_closed_at",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_resolved_at",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_assigned_to_id",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_status",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_priority",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_severity",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_alert_id",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_incident_id",
        table_name="incidents",
    )

    op.drop_index(
        "ix_incidents_id",
        table_name="incidents",
    )

    op.drop_table("incidents")