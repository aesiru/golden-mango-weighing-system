"""add notification system redesign

Revision ID: 8f4a660c3d25
Revises: b7c91f4d2e10
Create Date: 2026-04-01 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f4a660c3d25"
down_revision: Union[str, None] = "b7c91f4d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_rule table
    op.create_table(
        "notification_rule",
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("target_roles", sa.JSON(), nullable=True),
        sa.Column("target_user_ids", sa.JSON(), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_rule_entity_type"), "notification_rule", ["entity_type"], unique=False)
    op.create_index(op.f("ix_notification_rule_event"), "notification_rule", ["event"], unique=False)

    # Create notification_user_preference table
    op.create_table(
        "notification_user_preference",
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("frontend_enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_user_preference_user_id"), "notification_user_preference", ["user_id"], unique=False)

    # Create frontend_notification table
    op.create_table(
        "frontend_notification",
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_frontend_notification_user_id"), "frontend_notification", ["user_id"], unique=False)
    op.create_index(op.f("ix_frontend_notification_is_read"), "frontend_notification", ["is_read"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_frontend_notification_is_read"), table_name="frontend_notification")
    op.drop_index(op.f("ix_frontend_notification_user_id"), table_name="frontend_notification")
    op.drop_table("frontend_notification")
    op.drop_index(op.f("ix_notification_user_preference_user_id"), table_name="notification_user_preference")
    op.drop_table("notification_user_preference")
    op.drop_index(op.f("ix_notification_rule_event"), table_name="notification_rule")
    op.drop_index(op.f("ix_notification_rule_entity_type"), table_name="notification_rule")
    op.drop_table("notification_rule")
