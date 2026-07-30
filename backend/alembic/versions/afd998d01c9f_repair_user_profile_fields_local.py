"""repair_user_profile_fields_local

Revision ID: afd998d01c9f
Revises: 6571f4dfd939
Create Date: 2026-03-12 09:26:48.245438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'afd998d01c9f'
down_revision: Union[str, None] = '6571f4dfd939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}
    if "first_name" not in existing:
        op.add_column('users', sa.Column('first_name', sa.String(length=100), nullable=True))
    if "last_name" not in existing:
        op.add_column('users', sa.Column('last_name', sa.String(length=100), nullable=True))
    if "contact_number" not in existing:
        op.add_column('users', sa.Column('contact_number', sa.String(length=50), nullable=True))
    if "department" not in existing:
        op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))
    if "site" not in existing:
        op.add_column('users', sa.Column('site', sa.String(length=100), nullable=True))
    if "employee_id" not in existing:
        op.add_column('users', sa.Column('employee_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}
    if "employee_id" in existing:
        op.drop_column('users', 'employee_id')
    if "site" in existing:
        op.drop_column('users', 'site')
    if "department" in existing:
        op.drop_column('users', 'department')
    if "contact_number" in existing:
        op.drop_column('users', 'contact_number')
    if "last_name" in existing:
        op.drop_column('users', 'last_name')
    if "first_name" in existing:
        op.drop_column('users', 'first_name')
