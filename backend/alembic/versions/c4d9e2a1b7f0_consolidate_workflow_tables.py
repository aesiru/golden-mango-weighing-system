"""consolidate workflow tables to canonical plural names

Revision ID: c4d9e2a1b7f0
Revises: a3f1b2c4d5e6
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "c4d9e2a1b7f0"
down_revision = "a3f1b2c4d5e6"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return table_name in inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    # Consolidate workflow states into canonical table.
    if _table_exists(bind, "workflow_state") and _table_exists(bind, "workflow_states"):
        bind.execute(text("""
            INSERT INTO workflow_states (id, label, slug, color, created_at, updated_at)
            SELECT s.id, s.label, s.slug, s.color, s.created_at, s.updated_at
            FROM workflow_state s
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_states t WHERE t.id = s.id
            )
        """))

    # Consolidate workflow actions into canonical table.
    if _table_exists(bind, "workflow_action") and _table_exists(bind, "workflow_actions"):
        bind.execute(text("""
            INSERT INTO workflow_actions (id, label, slug, created_at, updated_at)
            SELECT s.id, s.label, s.slug, s.created_at, s.updated_at
            FROM workflow_action s
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_actions t WHERE t.id = s.id
            )
        """))

    if _table_exists(bind, "workflow_state"):
        op.drop_table("workflow_state")

    if _table_exists(bind, "workflow_action"):
        op.drop_table("workflow_action")


def downgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "workflow_state"):
        op.create_table(
            "workflow_state",
            sa.Column("id", sa.String(length=50), primary_key=True, nullable=False),
            sa.Column("label", sa.String(length=255), nullable=True),
            sa.Column("slug", sa.String(length=255), nullable=True),
            sa.Column("color", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if not _table_exists(bind, "workflow_action"):
        op.create_table(
            "workflow_action",
            sa.Column("id", sa.String(length=50), primary_key=True, nullable=False),
            sa.Column("label", sa.String(length=255), nullable=True),
            sa.Column("slug", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if _table_exists(bind, "workflow_states"):
        bind.execute(text("""
            INSERT INTO workflow_state (id, label, slug, color, created_at, updated_at)
            SELECT s.id, s.label, s.slug, s.color, s.created_at, s.updated_at
            FROM workflow_states s
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_state t WHERE t.id = s.id
            )
        """))

    if _table_exists(bind, "workflow_actions"):
        bind.execute(text("""
            INSERT INTO workflow_action (id, label, slug, created_at, updated_at)
            SELECT s.id, s.label, s.slug, s.created_at, s.updated_at
            FROM workflow_actions s
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_action t WHERE t.id = s.id
            )
        """))
