"""Add audit_log table

Revision ID: add_audit_log_table
Revises: add_attachment_table
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_audit_log_table'
down_revision: Union[str, None] = 'add_attachment_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_name', sa.String(100), nullable=False, index=True),
        sa.Column('record_id', sa.String(50), nullable=False, index=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('before_snapshot', sa.Text(), nullable=True),
        sa.Column('after_snapshot', sa.Text(), nullable=True),
        sa.Column('changed_fields', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_audit_log_entity_record', 'audit_log', ['entity_name', 'record_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_log_entity_record', table_name='audit_log')
    op.drop_table('audit_log')
