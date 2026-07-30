"""Add created_by and last_modified_by to domain tables

Revision ID: 4c2a6d9e1f0b
Revises: f1a2b3c4d5e6
Create Date: 2026-04-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "4c2a6d9e1f0b"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SKIP_TABLES = {
    "alembic_version",
    "core_audit_log",
    "core_diagram_layout",
    "core_email_log",
    "core_entity_order",
    "core_entity_permissions",
    "core_error_log",
    "core_module_order",
    "core_notification_subscription",
    "core_roles",
    "core_scheduled_job_log",
    "core_user_roles",
    "core_users",
    "core_workflow",
    "core_workflow_action",
    "core_workflow_state",
    "core_workflow_state_link",
    "core_workflow_transition",
}


def _target_tables(inspector: inspect) -> list[str]:
    tables: list[str] = []
    for table_name in inspector.get_table_names():
        if table_name in SKIP_TABLES or table_name.startswith("core_"):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if {"id", "created_at", "updated_at"}.issubset(columns):
            tables.append(table_name)
    return tables


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name in _target_tables(inspector):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "created_by" not in columns:
            op.add_column(table_name, sa.Column("created_by", sa.String(length=36), nullable=True))
        if "last_modified_by" not in columns:
            op.add_column(table_name, sa.Column("last_modified_by", sa.String(length=36), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name in _target_tables(inspector):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "last_modified_by" in columns:
            op.drop_column(table_name, "last_modified_by")
        if "created_by" in columns:
            op.drop_column(table_name, "created_by")