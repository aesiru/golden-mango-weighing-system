"""merge heads before notification_subscription

Revision ID: b0e2d66f8106
Revises: 3fa667fc39b4, b7c91f4d2e10, update_workflow_state_colors
Create Date: 2026-04-01 15:51:51.192925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0e2d66f8106'
down_revision: Union[str, None] = ('3fa667fc39b4', 'b7c91f4d2e10', 'update_workflow_state_colors')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
