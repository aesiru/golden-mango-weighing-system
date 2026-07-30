"""catalog notifications: subscription user_id, drop redesign tables

Revision ID: e4f8a1c2b9d0
Revises: 6b7306ee32c1
Create Date: 2026-04-05 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f8a1c2b9d0"
down_revision: Union[str, None] = "6b7306ee32c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS frontend_notification"))
    op.execute(sa.text("DROP TABLE IF EXISTS notification_user_preference"))
    op.execute(sa.text("DROP TABLE IF EXISTS notification_rule"))

    op.execute(sa.text("DELETE FROM notification_subscription"))

    op.drop_index(op.f("ix_notification_subscription_recipient_email"), table_name="notification_subscription")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("notification_subscription", schema=None) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=False))
            batch_op.alter_column(
                "recipient_email",
                existing_type=sa.String(length=255),
                nullable=True,
            )
            batch_op.create_foreign_key(
                "fk_notification_subscription_user_id_users",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_unique_constraint(
                "uq_notification_subscription_user_entity_event",
                ["user_id", "entity_type", "event"],
            )
    else:
        op.add_column(
            "notification_subscription",
            sa.Column("user_id", sa.String(length=36), nullable=False),
        )
        op.alter_column(
            "notification_subscription",
            "recipient_email",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        op.create_foreign_key(
            "fk_notification_subscription_user_id_users",
            "notification_subscription",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_unique_constraint(
            "uq_notification_subscription_user_entity_event",
            "notification_subscription",
            ["user_id", "entity_type", "event"],
        )

    op.create_index(
        op.f("ix_notification_subscription_user_id"),
        "notification_subscription",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f("ix_notification_subscription_user_id"), table_name="notification_subscription")

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("notification_subscription", schema=None) as batch_op:
            batch_op.drop_constraint("uq_notification_subscription_user_entity_event", type_="unique")
            batch_op.drop_constraint("fk_notification_subscription_user_id_users", type_="foreignkey")
            batch_op.alter_column(
                "recipient_email",
                existing_type=sa.String(length=255),
                nullable=False,
            )
            batch_op.drop_column("user_id")
    else:
        op.drop_constraint("uq_notification_subscription_user_entity_event", "notification_subscription", type_="unique")
        op.drop_constraint("fk_notification_subscription_user_id_users", "notification_subscription", type_="foreignkey")
        op.drop_column("notification_subscription", "user_id")
        op.alter_column(
            "notification_subscription",
            "recipient_email",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    op.create_index(
        op.f("ix_notification_subscription_recipient_email"),
        "notification_subscription",
        ["recipient_email"],
        unique=False,
    )

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
    op.create_index(
        op.f("ix_notification_user_preference_user_id"),
        "notification_user_preference",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "frontend_notification",
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_frontend_notification_user_id"), "frontend_notification", ["user_id"], unique=False)
    op.create_index(op.f("ix_frontend_notification_is_read"), "frontend_notification", ["is_read"], unique=False)
