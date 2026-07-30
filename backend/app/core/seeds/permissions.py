"""
Seed: Entity Permissions
========================
Creates the default role-entity permission matrix.
Idempotent — skips existing role+entity combinations.

SystemManager  → full CRUD + admin entities + in_sidebar
Technician     → CRUD on operational entities (no admin), in_sidebar
Viewer         → read-only on operational entities, in_sidebar
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.core.framework.models.auth import Role, EntityPermission

# No operational EAM modules remain in the core framework.
# The core framework currently only seeds admin entities and workflow infrastructure.
OPERATIONAL_ENTITIES = []

# Entities only SystemManager can access
ADMIN_ENTITIES = [
    "user",
    "role",
    "entity_permission",
    "audit_log",
    "error_log",
    "api_key",
]

_FULL = dict(
    can_read=True, can_create=True, can_update=True, can_delete=True,
    can_select=True, can_export=True, can_import=True, in_sidebar=True,
)
_CRUD = dict(
    can_read=True, can_create=True, can_update=True, can_delete=False,
    can_select=True, can_export=True, can_import=False, in_sidebar=True,
)
_READ = dict(
    can_read=True, can_create=False, can_update=False, can_delete=False,
    can_select=True, can_export=True, can_import=False, in_sidebar=True,
)
_NONE = dict(
    can_read=False, can_create=False, can_update=False, can_delete=False,
    can_select=False, can_export=False, can_import=False, in_sidebar=False,
)


async def seed_entity_permissions(db: AsyncSession) -> SeedResult:
    """Create default entity permissions per role. Skips existing role+entity combos."""
    result = SeedResult(entity="EntityPermission")

    roles_result = await db.execute(select(Role))
    roles = {r.name: r for r in roles_result.scalars().all()}

    permission_matrix = []

    # SystemManager: full access to all (operational + admin)
    sm = roles.get("SystemManager")
    if sm:
        for entity in OPERATIONAL_ENTITIES + ADMIN_ENTITIES:
            permission_matrix.append((sm, entity, _FULL))

    # Technician: CRUD on operational, no admin
    tech = roles.get("Technician")
    if tech:
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append((tech, entity, _CRUD))

    # Viewer: read-only on operational, no admin
    viewer = roles.get("Viewer")
    if viewer:
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append((viewer, entity, _READ))

    for role, entity_name, perms in permission_matrix:
        existing = await db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id == role.id)
            .where(EntityPermission.entity_name == entity_name)
        )
        if existing.scalar_one_or_none():
            result.skipped += 1
            continue

        db.add(EntityPermission(role_id=role.id, entity_name=entity_name, **perms))
        result.created += 1

    await db.commit()
    return result
