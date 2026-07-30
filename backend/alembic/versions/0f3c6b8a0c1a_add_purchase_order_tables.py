"""Add purchase_order and purchase_order_line tables

Revision ID: 0f3c6b8a0c1a
Revises: b4513178f86f
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "0f3c6b8a0c1a"
down_revision: Union[str, None] = "b4513178f86f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "purchase_order" not in existing_tables:
        op.create_table(
            "purchase_order",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("workflow_state", sa.String(length=255), nullable=True),
            sa.Column("source_rfq", sa.String(length=50), nullable=True),
            sa.Column("vendor", sa.String(length=50), nullable=True),
            sa.Column("vendor_name", sa.String(length=255), nullable=True),
            sa.Column("date_ordered", sa.Date(), nullable=True),
            sa.Column("total_amount", sa.Float(), nullable=True),
            sa.Column("site", sa.String(length=50), nullable=False),
            sa.Column("department", sa.String(length=50), nullable=False),
            sa.Column("cost_code", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["vendor"], ["vendor.id"]),
            sa.ForeignKeyConstraint(["site"], ["site.id"]),
            sa.ForeignKeyConstraint(["department"], ["department.id"]),
            sa.ForeignKeyConstraint(["cost_code"], ["cost_code.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_po_indexes = {ix["name"] for ix in inspector.get_indexes("purchase_order")} if "purchase_order" in existing_tables else set()
    if "ix_purchase_order_vendor" not in existing_po_indexes:
        op.create_index("ix_purchase_order_vendor", "purchase_order", ["vendor"])
    if "ix_purchase_order_date_ordered" not in existing_po_indexes:
        op.create_index("ix_purchase_order_date_ordered", "purchase_order", ["date_ordered"])
    if "ix_purchase_order_workflow_state" not in existing_po_indexes:
        op.create_index("ix_purchase_order_workflow_state", "purchase_order", ["workflow_state"])

    if "purchase_order_line" not in existing_tables:
        op.create_table(
            "purchase_order_line",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("workflow_state", sa.String(length=255), nullable=True),
            sa.Column("po_id", sa.String(length=50), nullable=False),
            sa.Column("pr_line_id", sa.String(length=50), nullable=True),
            sa.Column("line_row_num", sa.Integer(), nullable=True),
            sa.Column("financial_asset_number", sa.String(length=255), nullable=True),
            sa.Column("item_id", sa.String(length=50), nullable=True),
            sa.Column("item_description", sa.Text(), nullable=True),
            sa.Column("quantity_ordered", sa.Integer(), nullable=True),
            sa.Column("price", sa.Float(), nullable=True),
            sa.Column("quantity_received", sa.Integer(), nullable=True),
            sa.Column("site", sa.String(length=50), nullable=False),
            sa.Column("department", sa.String(length=50), nullable=False),
            sa.Column("cost_code", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["po_id"], ["purchase_order.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["pr_line_id"], ["purchase_request_line.id"]),
            sa.ForeignKeyConstraint(["item_id"], ["item.id"]),
            sa.ForeignKeyConstraint(["site"], ["site.id"]),
            sa.ForeignKeyConstraint(["department"], ["department.id"]),
            sa.ForeignKeyConstraint(["cost_code"], ["cost_code.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_pol_indexes = {ix["name"] for ix in inspector.get_indexes("purchase_order_line")} if "purchase_order_line" in existing_tables else set()
    if "ix_purchase_order_line_po_id" not in existing_pol_indexes:
        op.create_index("ix_purchase_order_line_po_id", "purchase_order_line", ["po_id"])
    if "ix_purchase_order_line_item_id" not in existing_pol_indexes:
        op.create_index("ix_purchase_order_line_item_id", "purchase_order_line", ["item_id"])
    if "ix_purchase_order_line_workflow_state" not in existing_pol_indexes:
        op.create_index("ix_purchase_order_line_workflow_state", "purchase_order_line", ["workflow_state"])


def downgrade() -> None:
    op.drop_index("ix_purchase_order_line_workflow_state", table_name="purchase_order_line")
    op.drop_index("ix_purchase_order_line_item_id", table_name="purchase_order_line")
    op.drop_index("ix_purchase_order_line_po_id", table_name="purchase_order_line")
    op.drop_table("purchase_order_line")

    op.drop_index("ix_purchase_order_workflow_state", table_name="purchase_order")
    op.drop_index("ix_purchase_order_date_ordered", table_name="purchase_order")
    op.drop_index("ix_purchase_order_vendor", table_name="purchase_order")
    op.drop_table("purchase_order")
