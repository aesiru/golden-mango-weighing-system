"""Refactor workflow to global shared-entity model

Revision ID: 003_workflow_global
Revises: 002_workflow
Create Date: 2026-01-27

Drops old workflow tables and creates new global workflow management schema:
- workflow_states (global)
- workflow_actions (global)
- workflows (per entity)
- workflow_state_links (junction)
- workflow_transitions (references global states/actions)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003_workflow_global'
down_revision: Union[str, None] = '26397e9525bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old workflow tables (order matters due to FKs)
    op.drop_table('workflow_transition_roles', if_exists=True)
    op.drop_table('workflow_transitions', if_exists=True)
    op.drop_table('workflow_states', if_exists=True)
    op.drop_table('workflows', if_exists=True)
    op.drop_table('entity_workflows', if_exists=True)
    op.drop_table('server_actions', if_exists=True)
    
    # Create new global workflow_states table
    op.create_table('workflow_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True, default='gray'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    # Create new global workflow_actions table
    op.create_table('workflow_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    # Create workflows table (per entity)
    op.create_table('workflows',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('target_entity', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_entity')
    )
    
    # Create workflow_state_links junction table
    op.create_table('workflow_state_links',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('state_id', sa.String(length=36), nullable=False),
        sa.Column('is_initial', sa.Boolean(), nullable=False, default=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['state_id'], ['workflow_states.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_id', 'state_id', name='uq_workflow_state')
    )
    op.create_index('ix_workflow_state_links_workflow', 'workflow_state_links', ['workflow_id'])
    
    # Create workflow_transitions table
    op.create_table('workflow_transitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('from_state_id', sa.String(length=36), nullable=False),
        sa.Column('action_id', sa.String(length=36), nullable=False),
        sa.Column('to_state_id', sa.String(length=36), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_state_id'], ['workflow_states.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['action_id'], ['workflow_actions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['to_state_id'], ['workflow_states.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_transitions_workflow', 'workflow_transitions', ['workflow_id'])


def downgrade() -> None:
    # Drop new tables
    op.drop_index('ix_workflow_transitions_workflow', table_name='workflow_transitions')
    op.drop_table('workflow_transitions')
    op.drop_index('ix_workflow_state_links_workflow', table_name='workflow_state_links')
    op.drop_table('workflow_state_links')
    op.drop_table('workflows')
    op.drop_table('workflow_actions')
    op.drop_table('workflow_states')
    
    # Recreate old tables (simplified - just structure)
    op.create_table('workflows',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('state_field', sa.String(length=100), nullable=False),
        sa.Column('default_state', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_name')
    )
    
    op.create_table('workflow_states',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('is_terminal', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('workflow_transitions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('from_state_id', sa.String(length=36), nullable=False),
        sa.Column('to_state_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['from_state_id'], ['workflow_states.id']),
        sa.ForeignKeyConstraint(['to_state_id'], ['workflow_states.id']),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('workflow_transition_roles',
        sa.Column('transition_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.ForeignKeyConstraint(['transition_id'], ['workflow_transitions.id']),
        sa.PrimaryKeyConstraint('transition_id', 'role_id')
    )
    
    op.create_table('server_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('handler_path', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
