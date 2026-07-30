"""Add workflow tables

Revision ID: 002_workflow
Revises: 001_initial
Create Date: 2026-01-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_workflow'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workflows table
    op.create_table('workflows',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('state_field', sa.String(length=100), nullable=False, default='status'),
        sa.Column('default_state', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_name')
    )
    
    # Create workflow_states table
    op.create_table('workflow_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('is_terminal', sa.Boolean(), nullable=False, default=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create workflow_transitions table
    op.create_table('workflow_transitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('from_state_id', sa.String(length=36), nullable=False),
        sa.Column('to_state_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['from_state_id'], ['workflow_states.id'], ),
        sa.ForeignKeyConstraint(['to_state_id'], ['workflow_states.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create workflow_transition_roles junction table
    op.create_table('workflow_transition_roles',
        sa.Column('transition_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['transition_id'], ['workflow_transitions.id'], ),
        sa.PrimaryKeyConstraint('transition_id', 'role_id')
    )
    
    # Create server_actions table
    op.create_table('server_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('handler_path', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('server_actions')
    op.drop_table('workflow_transition_roles')
    op.drop_table('workflow_transitions')
    op.drop_table('workflow_states')
    op.drop_table('workflows')
