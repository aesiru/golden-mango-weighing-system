"""Convert UUID columns to VARCHAR(50) for masterfiles seeding

Revision ID: b4513178f86f
Revises: aef1068f18bd
Create Date: 2026-02-04

This project uses Frappe-style human-readable string IDs (e.g., ORG-00001) as
primary keys and foreign keys. Some environments may have been initialized with
UUID-typed columns, which breaks Excel seeding.

This migration:
- Drops all foreign key constraints in schema `public`
- Converts every `uuid` column in schema `public` to `VARCHAR(50)` using ::text
- Recreates the foreign key constraints

It also enforces nullable organization name fields to match masterfiles.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4513178f86f"
down_revision: Union[str, None] = "aef1068f18bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fetchall(conn, sql: str, params: dict | None = None):
    return conn.execute(sa.text(sql), params or {}).mappings().all()


def upgrade() -> None:
    conn = op.get_bind()

    # Collect FK definitions in public schema
    fks = _fetchall(
        conn,
        """
        SELECT
          c.conname AS constraint_name,
          n.nspname AS schema_name,
          rel.relname AS table_name,
          array_agg(att.attname ORDER BY u.ord) AS columns,
          rel2.relname AS ref_table,
          array_agg(att2.attname ORDER BY u.ord) AS ref_columns,
          c.confdeltype AS confdeltype,
          c.confupdtype AS confupdtype
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        JOIN pg_class rel ON rel.oid = c.conrelid
        JOIN pg_class rel2 ON rel2.oid = c.confrelid
        JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS u(attnum, ord) ON true
        JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = u.attnum
        JOIN LATERAL unnest(c.confkey) WITH ORDINALITY AS u2(attnum, ord) ON u2.ord = u.ord
        JOIN pg_attribute att2 ON att2.attrelid = rel2.oid AND att2.attnum = u2.attnum
        WHERE c.contype = 'f'
          AND n.nspname = 'public'
        GROUP BY c.conname, n.nspname, rel.relname, rel2.relname, c.confdeltype, c.confupdtype
        ORDER BY rel.relname, c.conname
        """,
    )

    # Drop all FKs
    for fk in fks:
        op.execute(
            sa.text(
                f'ALTER TABLE "{fk["schema_name"]}"."{fk["table_name"]}" DROP CONSTRAINT "{fk["constraint_name"]}"'
            )
        )

    # Convert UUID columns
    uuid_cols = _fetchall(
        conn,
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND udt_name = 'uuid'
        ORDER BY table_name, ordinal_position
        """,
    )

    for col in uuid_cols:
        table = col["table_name"]
        column = col["column_name"]
        op.execute(
            sa.text(
                f'ALTER TABLE "public"."{table}" ALTER COLUMN "{column}" TYPE VARCHAR(50) USING "{column}"::text'
            )
        )

    # Ensure organization name fields nullable (matches model + workbook)
    try:
        op.alter_column("organization", "organization_name", existing_type=sa.String(length=255), nullable=True)
    except Exception:
        pass
    try:
        op.alter_column("organization", "legal_name", existing_type=sa.String(length=255), nullable=True)
    except Exception:
        pass

    # Recreate FKs
    def _action(code: str, kind: str) -> str | None:
        mapping = {
            "a": "NO ACTION",
            "r": "RESTRICT",
            "c": "CASCADE",
            "n": "SET NULL",
            "d": "SET DEFAULT",
        }
        act = mapping.get(code)
        if not act or act == "NO ACTION":
            return None
        return f"ON {kind} {act}"

    for fk in fks:
        cols = ", ".join([f'"{c}"' for c in fk["columns"]])
        ref_cols = ", ".join([f'"{c}"' for c in fk["ref_columns"]])
        on_delete = _action(fk["confdeltype"], "DELETE")
        on_update = _action(fk["confupdtype"], "UPDATE")
        actions = " ".join([a for a in [on_delete, on_update] if a])

        op.execute(
            sa.text(
                " ".join(
                    [
                        f'ALTER TABLE "{fk["schema_name"]}"."{fk["table_name"]}"',
                        f'ADD CONSTRAINT "{fk["constraint_name"]}"',
                        f'FOREIGN KEY ({cols})',
                        f'REFERENCES "{fk["schema_name"]}"."{fk["ref_table"]}" ({ref_cols})',
                        actions,
                    ]
                ).strip()
            )
        )


def downgrade() -> None:
    # Reverting VARCHAR(50) back to UUID is unsafe and lossy.
    # Keep this as a no-op by design.
    pass
