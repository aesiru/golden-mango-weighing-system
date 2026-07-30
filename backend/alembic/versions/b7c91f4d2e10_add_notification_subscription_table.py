"""add notification subscription table

Revision ID: b7c91f4d2e10
Revises: 532e7889b6c1
Create Date: 2026-04-01 15:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c91f4d2e10"
down_revision: Union[str, None] = "532e7889b6c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_subscription",
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_subscription_entity_type"), "notification_subscription", ["entity_type"], unique=False)
    op.create_index(op.f("ix_notification_subscription_entity_id"), "notification_subscription", ["entity_id"], unique=False)
    op.create_index(op.f("ix_notification_subscription_event"), "notification_subscription", ["event"], unique=False)
    op.create_index(op.f("ix_notification_subscription_recipient_email"), "notification_subscription", ["recipient_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_subscription_recipient_email"), table_name="notification_subscription")
    op.drop_index(op.f("ix_notification_subscription_event"), table_name="notification_subscription")
    op.drop_index(op.f("ix_notification_subscription_entity_id"), table_name="notification_subscription")
    op.drop_index(op.f("ix_notification_subscription_entity_type"), table_name="notification_subscription")
    op.drop_table("notification_subscription")
