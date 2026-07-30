"""add can_select, can_export, can_import to entity_permissions

Revision ID: a3f1b2c4d5e6
Revises: 72d1fcf623bc
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f1b2c4d5e6'
down_revision = '72d1fcf623bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('entity_permissions', sa.Column('can_select', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('entity_permissions', sa.Column('can_export', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('entity_permissions', sa.Column('can_import', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('entity_permissions', 'can_import')
    op.drop_column('entity_permissions', 'can_export')
    op.drop_column('entity_permissions', 'can_select')
