"""Add attachment table

Revision ID: add_attachment_table
Revises: add_missing_rfq_fields
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_attachment_table'
down_revision: Union[str, None] = 'add_missing_rfq_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'attachment',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('entity_name', sa.String(100), nullable=False, index=True),
        sa.Column('record_id', sa.String(50), nullable=False, index=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('uploaded_by', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_attachment_entity_record', 'attachment', ['entity_name', 'record_id'])


def downgrade() -> None:
    op.drop_index('ix_attachment_entity_record', table_name='attachment')
    op.drop_table('attachment')
