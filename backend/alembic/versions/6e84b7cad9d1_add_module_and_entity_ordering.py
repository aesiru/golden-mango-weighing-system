"""add_module_and_entity_ordering

Revision ID: 6e84b7cad9d1
Revises: 004_nullable
Create Date: 2026-01-29 16:28:17.465088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e84b7cad9d1'
down_revision: Union[str, None] = '004_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'module_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('module_name', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('module_name', name='uq_module_name')
    )
    
    op.create_table(
        'entity_orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('entity_name', sa.String(100), nullable=False),
        sa.Column('module_name', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('entity_name', name='uq_entity_name')
    )


def downgrade() -> None:
    op.drop_table('entity_orders')
    op.drop_table('module_orders')
