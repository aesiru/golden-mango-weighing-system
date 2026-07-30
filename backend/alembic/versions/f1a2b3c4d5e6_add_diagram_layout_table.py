"""add diagram layout table

Revision ID: f1a2b3c4d5e6
Revises: e4f8a1c2b9d0
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e4f8a1c2b9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'core_diagram_layout',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_core_diagram_layout_created_by'), 'core_diagram_layout', ['created_by'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_core_diagram_layout_created_by'), table_name='core_diagram_layout')
    op.drop_table('core_diagram_layout')
