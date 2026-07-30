"""drop maintenance_plan.model_name

Revision ID: c7b42d8e91aa
Revises: a2f3e3ff8feb
Create Date: 2026-04-22 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7b42d8e91aa'
down_revision: Union[str, None] = 'a2f3e3ff8feb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('maintenance_plan', 'model_name')


def downgrade() -> None:
    op.add_column(
        'maintenance_plan',
        sa.Column('model_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    )
