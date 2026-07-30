"""merge heads

Revision ID: 985912219690
Revises: 985912219691, b9556313161c
Create Date: 2026-02-26 15:19:16.423849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '985912219690'
down_revision: Union[str, None] = ('985912219691', 'b9556313161c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
