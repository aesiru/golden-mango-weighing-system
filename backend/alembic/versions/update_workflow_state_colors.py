"""Update workflow state colors to Nuxt UI defaults

Revision ID: update_workflow_state_colors
Revises: a3f1b2c4d5e6
Create Date: 2026-04-01 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = 'update_workflow_state_colors'
down_revision = 'a3f1b2c4d5e6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Map common hex colors to Nuxt UI colors
    color_mapping = {
        '#3B82F6': 'primary',    # blue
        '#10B981': 'success',    # green  
        '#F59E0B': 'warning',    # amber/yellow
        '#EF4444': 'error',      # red
        '#8B5CF6': 'secondary',  # purple
        '#6B7280': 'neutral',    # gray
        '#0EA5E9': 'info',       # cyan/sky blue
        '#F97316': 'warning',    # orange
        '#EC4899': 'secondary',  # pink
        '#6366F1': 'secondary',  # indigo
        '#84CC16': 'success',    # lime
        '#14B8A6': 'info',       # teal
        '#A855F7': 'secondary',  # violet
        '#F43F5E': 'error',      # rose
    }
    
    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Update existing workflow states
        for hex_color, nuxt_color in color_mapping.items():
            stmt = sa.text("UPDATE workflow_states SET color = :nuxt_color WHERE color = :hex_color")
            session.execute(stmt, {"nuxt_color": nuxt_color, "hex_color": hex_color})
        
        # Update any remaining hex colors to neutral
        stmt = sa.text("UPDATE workflow_states SET color = 'neutral' WHERE color LIKE '#%'")
        session.execute(stmt)
        
        # Update old color names to Nuxt UI equivalents
        color_name_mapping = {
            'blue': 'primary',
            'green': 'success', 
            'yellow': 'warning',
            'red': 'error',
            'purple': 'secondary',
            'gray': 'neutral',
            'grey': 'neutral',
            'cyan': 'info',
            'orange': 'warning',
            'pink': 'secondary',
            'lime': 'success',
            'teal': 'info',
            'violet': 'secondary',
            'indigo': 'secondary',
            'rose': 'error',
            'slate': 'neutral',
            'zinc': 'neutral',
        }
        
        for old_color, nuxt_color in color_name_mapping.items():
            stmt = sa.text("UPDATE workflow_states SET color = :nuxt_color WHERE color = :old_color")
            session.execute(stmt, {"nuxt_color": nuxt_color, "old_color": old_color})
        
        session.commit()
    finally:
        session.close()

def downgrade() -> None:
    # Revert back to hex colors (simplified - would need original values to perfectly restore)
    revert_mapping = {
        'primary': '#3B82F6',
        'secondary': '#8B5CF6', 
        'success': '#10B981',
        'info': '#0EA5E9',
        'warning': '#F59E0B',
        'error': '#EF4444',
        'neutral': '#6B7280',
    }
    
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        for nuxt_color, hex_color in revert_mapping.items():
            stmt = sa.text("UPDATE workflow_states SET color = :hex_color WHERE color = :nuxt_color")
            session.execute(stmt, {"hex_color": hex_color, "nuxt_color": nuxt_color})
        
        session.commit()
    finally:
        session.close()
