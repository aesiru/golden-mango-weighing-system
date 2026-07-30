"""Make all non-PK columns nullable for testing flexibility

Revision ID: 004_nullable
Revises: 3db2809e21cc
Create Date: 2026-01-29

This migration makes all non-primary-key columns nullable across all tables.
This allows for flexible testing where not all fields are required.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = '004_nullable'
down_revision: Union[str, None] = '003_workflow_global'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columns that should remain NOT NULL (system-critical)
EXCLUDE_COLUMNS = {
    'id',  # Primary keys
    'created_at',
    'updated_at',
}

# Tables to skip entirely
SKIP_TABLES = {
    'alembic_version',
    'series',  # Series table has special structure
}


def upgrade() -> None:
    """Make all non-PK, non-system columns nullable."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    for table_name in inspector.get_table_names():
        if table_name in SKIP_TABLES:
            continue
            
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint.get('constrained_columns', []))
        
        for col in columns:
            col_name = col['name']
            
            # Skip primary keys and excluded columns
            if col_name in pk_columns or col_name in EXCLUDE_COLUMNS:
                continue
            
            # Skip if already nullable
            if col.get('nullable', True):
                continue
            
            try:
                op.alter_column(
                    table_name,
                    col_name,
                    existing_type=col['type'],
                    nullable=True
                )
                print(f"  ✓ {table_name}.{col_name} -> nullable")
            except Exception as e:
                print(f"  ✗ {table_name}.{col_name}: {e}")


def downgrade() -> None:
    """Revert is complex - would need to track original nullable state.
    For safety, this is a no-op. Manual intervention required to restore NOT NULL constraints.
    """
    pass
