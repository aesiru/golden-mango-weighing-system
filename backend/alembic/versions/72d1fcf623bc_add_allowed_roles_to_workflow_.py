"""Add allowed_roles to workflow_transitions

Revision ID: 72d1fcf623bc
Revises: add_audit_log_table
Create Date: 2026-02-11 18:58:54.933884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '72d1fcf623bc'
down_revision: Union[str, None] = 'add_audit_log_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workflow_transitions', sa.Column('allowed_roles', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('workflow_transitions', 'allowed_roles')
