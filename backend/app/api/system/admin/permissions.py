"""
Permissions Router
==================
Entity permission management endpoints.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import User, Role, EntityPermission
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from .common import api_response

router = APIRouter(tags=["admin-permissions"])


@router.get("/permissions/entities")
async def get_entities_by_module(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get all entities grouped by module for permission management."""
    if not (current_user.is_superuser or "SystemManager" in (current_user.roles or [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.core.framework.models.ordering import ModuleOrder, EntityOrder
    
    entities = MetaRegistry.list_all()
    
    module_orders_result = await db.execute(select(ModuleOrder))
    module_orders = {mo.module_name: mo.sort_order for mo in module_orders_result.scalars().all()}
    
    entity_orders_result = await db.execute(select(EntityOrder))
    entity_orders = {eo.entity_name: eo.sort_order for eo in entity_orders_result.scalars().all()}
    
    rows = []
    for entity in entities:
        module = entity.module or "Other"
        entity_payload = {
            "name": entity.name,
            "label": entity.label,
            "module": module,
            "sort_order": entity_orders.get(entity.name, 999),
        }
        rows.append(entity_payload)
    
    rows.sort(key=lambda e: (module_orders.get(e["module"], 999), e["sort_order"]))
    
    return {
        "status": "success",
        "data": {
            "rows": rows,
            "total_entities": len(entities)
        }
    }


@router.get("/permissions/matrix")
async def get_permission_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get permission matrix for all roles and entities."""
    if not (current_user.is_superuser or "SystemManager" in (current_user.roles or [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    entities = MetaRegistry.list_all()
    entity_names = [e.name for e in entities]
    
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    
    matrix = []
    for role in roles:
        is_system_manager = role.name == "SystemManager"
        role_perms = {p.entity_name: p for p in role.permissions}
        row = {
            "role_id": role.id,
            "role_name": role.name,
            "entities": {}
        }
        for entity_name in entity_names:
            perm = role_perms.get(entity_name)
            row["entities"][entity_name] = {
                "can_read": True if is_system_manager else (perm.can_read if perm else False),
                "can_create": True if is_system_manager else (perm.can_create if perm else False),
                "can_update": True if is_system_manager else (perm.can_update if perm else False),
                "can_delete": True if is_system_manager else (perm.can_delete if perm else False),
                "can_select": True if is_system_manager else (perm.can_select if perm else False),
                "can_export": True if is_system_manager else (perm.can_export if perm else False),
                "can_import": True if is_system_manager else (perm.can_import if perm else False),
                "in_sidebar": True if is_system_manager else (perm.in_sidebar if perm else False),
            }
        matrix.append(row)
    
    return api_response(
        status="success",
        message="Permissions retrieved successfully",
        data={
            "entities": entity_names,
            "matrix": matrix,
        }
    )


@router.get("/permissions/role/{role_id}")
async def get_role_permissions(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get all permissions for a specific role."""
    if not (current_user.is_superuser or "SystemManager" in (current_user.roles or [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    
    if not role:
        return {"status": "error", "message": "Role not found"}
    
    entities = MetaRegistry.list_all()
    entity_names = [e.name for e in entities]

    is_system_manager = role.name == "SystemManager"
    compact = {
        "can_read": [],
        "can_create": [],
        "can_update": [],
        "can_delete": [],
        "can_select": [],
        "can_export": [],
        "can_import": [],
        "in_sidebar": [],
    }

    if is_system_manager:
        for k in compact.keys():
            compact[k] = entity_names
    else:
        for perm in role.permissions:
            if perm.can_read:
                compact["can_read"].append(perm.entity_name)
            if perm.can_create:
                compact["can_create"].append(perm.entity_name)
            if perm.can_update:
                compact["can_update"].append(perm.entity_name)
            if perm.can_delete:
                compact["can_delete"].append(perm.entity_name)
            if perm.can_select:
                compact["can_select"].append(perm.entity_name)
            if perm.can_export:
                compact["can_export"].append(perm.entity_name)
            if perm.can_import:
                compact["can_import"].append(perm.entity_name)
            if perm.in_sidebar:
                compact["in_sidebar"].append(perm.entity_name)
    
    return api_response(
        status="success",
        message="Role permissions retrieved successfully",
        data={
            "role": {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            },
            "permissions": compact
        }
    )


@router.put("/permissions/role/{role_id}")
async def update_role_permissions(
    role_id: str,
    permissions_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update all permissions for a specific role."""
    if not (current_user.is_superuser or "SystemManager" in (current_user.roles or [])):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        return api_response(
            status="error",
            message="Role not found"
        )
    
    if role.name == "SystemManager":
        return api_response(
            status="error",
            message="Cannot modify SystemManager permissions"
        )
    
    # Delete existing permissions
    result = await db.execute(
        select(EntityPermission).where(EntityPermission.role_id == role_id)
    )
    existing_perms = result.scalars().all()
    for perm in existing_perms:
        await db.delete(perm)
    
    # Create new permissions (supports both formats)
    permissions = permissions_data.get("permissions", {})

    # Compact format: { can_read: [..], can_create: [..], ... }
    if isinstance(permissions, dict) and any(
        k in permissions for k in ["can_read", "can_create", "can_update", "can_delete", "can_select", "can_export", "can_import", "in_sidebar"]
    ):
        read_set = set(permissions.get("can_read", []) or [])
        create_set = set(permissions.get("can_create", []) or [])
        update_set = set(permissions.get("can_update", []) or [])
        delete_set = set(permissions.get("can_delete", []) or [])
        select_set = set(permissions.get("can_select", []) or [])
        export_set = set(permissions.get("can_export", []) or [])
        import_set = set(permissions.get("can_import", []) or [])
        sidebar_set = set(permissions.get("in_sidebar", []) or [])

        for entity_name in set().union(read_set, create_set, update_set, delete_set, select_set, export_set, import_set, sidebar_set):
            if entity_name in ["user", "role", "entity_permission"] and role.name != "SystemManager":
                continue

            permission = EntityPermission(
                role_id=role_id,
                entity_name=entity_name,
                can_read=entity_name in read_set,
                can_create=entity_name in create_set,
                can_update=entity_name in update_set,
                can_delete=entity_name in delete_set,
                can_select=entity_name in select_set,
                can_export=entity_name in export_set,
                can_import=entity_name in import_set,
                in_sidebar=entity_name in sidebar_set,
            )
            db.add(permission)
    else:
        # Legacy format: { entity_name: {can_read: bool, ...} }
        for entity_name, perm_data in permissions.items():
            if entity_name in ["user", "role", "entity_permission"] and role.name != "SystemManager":
                continue
            
            permission = EntityPermission(
                role_id=role_id,
                entity_name=entity_name,
                can_read=perm_data.get("can_read", False),
                can_create=perm_data.get("can_create", False),
                can_update=perm_data.get("can_update", False),
                can_delete=perm_data.get("can_delete", False),
                can_select=perm_data.get("can_select", False),
                can_export=perm_data.get("can_export", False),
                can_import=perm_data.get("can_import", False),
                in_sidebar=perm_data.get("in_sidebar", False),
            )
            db.add(permission)
    
    await db.commit()
    
    return api_response(
        status="success",
        message="Permissions updated successfully"
    )


@router.post("/permissions/set")
async def set_permission(
    role_id: str,
    entity_name: str,
    can_read: bool = False,
    can_create: bool = False,
    can_update: bool = False,
    can_delete: bool = False,
    in_sidebar: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Set permission for a role on an entity."""
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id == role_id)
        .where(EntityPermission.entity_name == entity_name)
    )
    perm = result.scalar_one_or_none()
    
    if perm:
        perm.can_read = can_read
        perm.can_create = can_create
        perm.can_update = can_update
        perm.can_delete = can_delete
        perm.in_sidebar = in_sidebar
    else:
        perm = EntityPermission(
            role_id=role_id,
            entity_name=entity_name,
            can_read=can_read,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
            in_sidebar=in_sidebar,
        )
        db.add(perm)
    
    await db.commit()
    await db.refresh(perm)
    
    return api_response(
        status="success",
        message="Permission updated successfully",
        data={
            "id": perm.id,
            "role_id": perm.role_id,
            "entity_name": perm.entity_name,
            "can_read": perm.can_read,
            "can_create": perm.can_create,
            "can_update": perm.can_update,
            "can_delete": perm.can_delete,
            "can_select": perm.can_select,
            "can_export": perm.can_export,
            "can_import": perm.can_import,
            "in_sidebar": perm.in_sidebar,
        }
    )


@router.post("/users/permissions/set")
async def set_user_permission(
    user_id: str,
    entity_name: str,
    can_read: bool = False,
    can_create: bool = False,
    can_update: bool = False,
    can_delete: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Set permission for a user on an entity by updating their primary role."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.roles:
        return ActionResponse(status="error", message="User not found or has no roles")
    
    primary_role = user.roles[0]
    
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id == primary_role.id)
        .where(EntityPermission.entity_name == entity_name)
    )
    perm = result.scalar_one_or_none()
    
    if perm:
        perm.can_read = can_read
        perm.can_create = can_create
        perm.can_update = can_update
        perm.can_delete = can_delete
    else:
        perm = EntityPermission(
            role_id=primary_role.id,
            entity_name=entity_name,
            can_read=can_read,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
        )
        db.add(perm)
    
    await db.commit()
    await db.refresh(perm)
    
    return ActionResponse(
        status="success",
        message="Permission updated",
        data={
            "entity_name": perm.entity_name,
            "can_read": perm.can_read,
            "can_create": perm.can_create,
            "can_update": perm.can_update,
            "can_delete": perm.can_delete,
        }
    )
