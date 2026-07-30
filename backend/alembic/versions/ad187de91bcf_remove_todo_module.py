"""Remove Todo module

Revision ID: ad187de91bcf
Revises: 8c6bb258c4c1
Create Date: 2026-01-22 09:33:39.997383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ad187de91bcf'
down_revision: Union[str, None] = '8c6bb258c4c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'todo_comment' in tables:
        op.drop_table('todo_comment')
    if 'todo' in tables:
        op.drop_table('todo')

    if 'project' in tables:
        columns = {c["name"] for c in inspector.get_columns("project")}
        if 'manager_id' not in columns:
            op.add_column('project', sa.Column('manager_id', sa.String(length=36), nullable=True))
            op.create_foreign_key(None, 'project', 'users', ['manager_id'], ['id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'project' in tables:
        columns = {c["name"] for c in inspector.get_columns("project")}
        if 'manager_id' in columns:
            foreign_keys = inspector.get_foreign_keys("project")
            for fk in foreign_keys:
                if fk.get("constrained_columns") == ["manager_id"]:
                    op.drop_constraint(fk["name"], 'project', type_='foreignkey')
                    break
            op.drop_column('project', 'manager_id')

    if 'todo' not in tables:
        op.create_table('todo',
    sa.Column('id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('priority', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('due_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('completed', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='todo_pkey'),
    postgresql_ignore_search_path=False
    )
    if 'todo_comment' not in tables:
        op.create_table('todo_comment',
    sa.Column('id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('todo_id', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('content', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('author', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['todo_id'], ['todo.id'], name=op.f('todo_comment_todo_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('todo_comment_pkey'))
    )
