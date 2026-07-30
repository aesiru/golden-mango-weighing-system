#!/usr/bin/env python3

import asyncio
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.loader import load_modules
from app.entities import load_all_entities
from app.meta.registry import MetaRegistry
from app.core.framework.models.auth import EntityPermission, Role


DEFAULT_INPUT = Path.home() / "Downloads" / "eam2.1" / "masterfiles" / "Role_Permission_reorganized.xlsx"
SHEET_NAME = "DocType x Role Matrix"


def normalize_entity_name(label: str) -> str:
    s = (label or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s_]", "", s)
    s = re.sub(r"\s+", "_", s)
    return s


def normalize_role_name(role: str) -> str:
    r = (role or "").strip()
    if r.lower().replace("_", " ") == "system manager":
        return "SystemManager"
    return r


async def get_or_create_role(db, role_name: str) -> Role:
    result = await db.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one_or_none()
    if role:
        return role
    role = Role(name=role_name, description=None, is_active=True)
    db.add(role)
    await db.flush()
    return role


async def upsert_entity_permission(
    db,
    role_id: str,
    entity_name: str,
    *,
    can_read: bool,
    can_create: bool,
    can_update: bool,
    can_delete: bool,
) -> None:
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id == role_id)
        .where(EntityPermission.entity_name == entity_name)
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.can_read = bool(can_read)
        perm.can_create = bool(can_create)
        perm.can_update = bool(can_update)
        perm.can_delete = bool(can_delete)
        return

    db.add(
        EntityPermission(
            role_id=role_id,
            entity_name=entity_name,
            can_read=bool(can_read),
            can_create=bool(can_create),
            can_update=bool(can_update),
            can_delete=bool(can_delete),
        )
    )


async def seed_from_matrix(input_path: Path) -> None:
    load_modules()
    load_all_entities()
    entities = MetaRegistry.list_all()
    entity_names = {e.name for e in entities}

    df = pd.read_excel(input_path, sheet_name=SHEET_NAME)
    if "Reference Document Type" not in df.columns:
        raise ValueError("Missing 'Reference Document Type' column")

    # Detect roles from matrix column names like: "Role Name__Create"
    roles = set()
    for c in df.columns:
        if "__" in str(c):
            roles.add(str(c).split("__", 1)[0].strip())
    roles = sorted(r for r in roles if r)

    crud_suffixes = {
        "Read": "can_read",
        "Create": "can_create",
        "Write": "can_update",
        "Delete": "can_delete",
    }

    async with async_session_maker() as db:
        # Create roles
        role_objs: dict[str, Role] = {}
        for role_label in roles:
            role_name = normalize_role_name(role_label)
            role_objs[role_label] = await get_or_create_role(db, role_name)

        await db.flush()

        skipped_doctypes = 0
        written_perms = 0

        for _, row in df.iterrows():
            doctype = str(row.get("Reference Document Type") or "").strip()
            if not doctype:
                continue

            entity_guess = normalize_entity_name(doctype)
            if entity_guess not in entity_names:
                # Some doctypes in the Excel are not real API entities (e.g. dashboard/import/meta tables)
                skipped_doctypes += 1
                continue

            for role_label, role_obj in role_objs.items():
                can_read = int(row.get(f"{role_label}__Read", 0) or 0) == 1
                can_create = int(row.get(f"{role_label}__Create", 0) or 0) == 1
                can_update = int(row.get(f"{role_label}__Write", 0) or 0) == 1
                can_delete = int(row.get(f"{role_label}__Delete", 0) or 0) == 1

                # Ignore non-CRUD columns as requested.
                await upsert_entity_permission(
                    db,
                    role_obj.id,
                    entity_guess,
                    can_read=can_read,
                    can_create=can_create,
                    can_update=can_update,
                    can_delete=can_delete,
                )
                written_perms += 1

        # Enforce SystemManager: full CRUD on all entities
        system_manager = await get_or_create_role(db, "SystemManager")
        for entity in entity_names:
            await upsert_entity_permission(
                db,
                system_manager.id,
                entity,
                can_read=True,
                can_create=True,
                can_update=True,
                can_delete=True,
            )

        await db.commit()

    print(f"✅ Roles created/verified: {len(roles)} (+SystemManager)")
    print(f"✅ Permissions written/updated (role x entity rows processed): {written_perms}")
    print(f"⏭️  Doctypes skipped (not registered entities): {skipped_doctypes}")


async def main() -> None:
    input_path = DEFAULT_INPUT
    await seed_from_matrix(input_path)


if __name__ == "__main__":
    asyncio.run(main())
