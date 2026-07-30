"""Add performance indexes on FK, created_at, and workflow_state columns.

Revision ID: 985912219691
Revises: 985912219690
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = "985912219691"
down_revision = "72d1fcf623bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create indexes for frequently queried columns across all entity tables."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    all_tables = inspector.get_table_names()

    # System/internal tables to skip
    skip_tables = {
        "alembic_version", "user_roles", "users", "roles",
        "entity_permissions", "workflow_states", "workflow_actions",
        "workflow_transitions", "workflows", "module_orders", "entity_orders",
    }

    for table_name in all_tables:
        if table_name in skip_tables:
            continue

        columns = {col["name"] for col in inspector.get_columns(table_name)}
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")
        }

        # 1. Index on created_at (used for default ORDER BY)
        if "created_at" in columns:
            idx_name = f"ix_{table_name}_created_at"
            if idx_name not in existing_indexes:
                op.create_index(idx_name, table_name, ["created_at"])

        # 2. Index on workflow_state (used for filtering)
        if "workflow_state" in columns:
            idx_name = f"ix_{table_name}_workflow_state"
            if idx_name not in existing_indexes:
                op.create_index(idx_name, table_name, ["workflow_state"])

        # 3. Index on all FK-like columns (ending in _id, referencing other entities)
        for col_name in columns:
            if not col_name.endswith("_id") or col_name == "id":
                continue
            idx_name = f"ix_{table_name}_{col_name}"
            if idx_name not in existing_indexes:
                op.create_index(idx_name, table_name, [col_name])


def downgrade() -> None:
    """Drop all indexes created by this migration."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    all_tables = inspector.get_table_names()

    skip_tables = {
        "alembic_version", "user_roles", "users", "roles",
        "entity_permissions", "workflow_states", "workflow_actions",
        "workflow_transitions", "workflows", "module_orders", "entity_orders",
    }

    for table_name in all_tables:
        if table_name in skip_tables:
            continue

        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")
        }
        columns = {col["name"] for col in inspector.get_columns(table_name)}

        if "created_at" in columns:
            idx_name = f"ix_{table_name}_created_at"
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name=table_name)

        if "workflow_state" in columns:
            idx_name = f"ix_{table_name}_workflow_state"
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name=table_name)

        for col_name in columns:
            if not col_name.endswith("_id") or col_name == "id":
                continue
            idx_name = f"ix_{table_name}_{col_name}"
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name=table_name)
