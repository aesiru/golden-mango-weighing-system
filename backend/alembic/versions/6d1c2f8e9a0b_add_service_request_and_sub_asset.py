"""Add service_request and sub_asset tables

Revision ID: 6d1c2f8e9a0b
Revises: 2a7d9c1f4e6b
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "6d1c2f8e9a0b"
down_revision: Union[str, None] = "2a7d9c1f4e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "service_request" not in existing_tables:
        op.create_table(
            "service_request",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("priority", sa.String(length=50), nullable=True),
            sa.Column("date_reported", sa.Date(), nullable=True),
            sa.Column("closed_date", sa.Date(), nullable=True),
            sa.Column("asset", sa.String(length=50), nullable=True),
            sa.Column("site", sa.String(length=50), nullable=True),
            sa.Column("location", sa.String(length=50), nullable=True),
            sa.Column("work_order", sa.String(length=50), nullable=True),
            sa.Column("incident", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["asset"], ["asset.id"]),
            sa.ForeignKeyConstraint(["site"], ["site.id"]),
            sa.ForeignKeyConstraint(["location"], ["location.id"]),
            sa.ForeignKeyConstraint(["work_order"], ["work_order.id"]),
            sa.ForeignKeyConstraint(["incident"], ["incident.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "sub_asset" not in existing_tables:
        op.create_table(
            "sub_asset",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("main_asset", sa.String(length=50), nullable=True),
            sa.Column("child_asset", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["main_asset"], ["asset.id"]),
            sa.ForeignKeyConstraint(["child_asset"], ["asset.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "sub_asset" in existing_tables:
        op.drop_table("sub_asset")

    if "service_request" in existing_tables:
        op.drop_table("service_request")
