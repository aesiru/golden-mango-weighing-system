"""merge heads for notification redesign

Revision ID: 6b7306ee32c1
Revises: 8f4a660c3d25, b0e2d66f8106
Create Date: 2026-04-01 16:00:13.001629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b7306ee32c1'
down_revision: Union[str, None] = ('8f4a660c3d25', 'b0e2d66f8106')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
