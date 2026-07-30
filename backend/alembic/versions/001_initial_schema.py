"""Initial schema with all models

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table first (no dependencies)
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create roles table (no dependencies)
    op.create_table('roles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create series table (no dependencies)
    op.create_table('series',
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('current', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('name')
    )
    
    # Create todo table (no dependencies)
    op.create_table('todo',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='open'),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create entity_permissions table (depends on roles)
    op.create_table('entity_permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('can_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('can_create', sa.Boolean(), nullable=False, default=False),
        sa.Column('can_update', sa.Boolean(), nullable=False, default=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False, default=False),
        sa.Column('in_sidebar', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create todo_comment table (depends on todo)
    op.create_table('todo_comment',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('todo_id', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('author', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['todo_id'], ['todo.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_roles junction table (depends on users and roles)
    op.create_table('user_roles',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )


def downgrade() -> None:
    op.drop_table('user_roles')
    op.drop_table('todo_comment')
    op.drop_table('entity_permissions')
    op.drop_table('todo')
    op.drop_table('series')
    op.drop_table('roles')
    op.drop_table('users')
