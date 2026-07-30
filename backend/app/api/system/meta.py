from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.meta.registry import MetaRegistry
from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import EntityPermission
from app.core.framework.models.ordering import ModuleOrder, EntityOrder
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository

router = APIRouter(prefix="/meta", tags=["meta"])

MODULE_LABELS = {
    "core": "Core",
}

MODULE_ICONS = {
    "core": "settings",
}

MODULE_ORDER_ALIASES = {}


def _module_order_key(module_name: str | None) -> str:
    if not module_name:
        return "other"
    return MODULE_ORDER_ALIASES.get(module_name, module_name)


def _aggregate_permissions(perms: list[EntityPermission]):
    agg: dict[str, dict[str, bool]] = {}
    for perm in perms:
        key = perm.entity_name
        if key not in agg:
            agg[key] = {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "can_select": False,
                "can_export": False,
                "can_import": False,
                "in_sidebar": False,
            }
        agg[key]["can_read"] = agg[key]["can_read"] or perm.can_read
        agg[key]["can_create"] = agg[key]["can_create"] or perm.can_create
        agg[key]["can_update"] = agg[key]["can_update"] or perm.can_update
        agg[key]["can_delete"] = agg[key]["can_delete"] or perm.can_delete
        agg[key]["can_select"] = agg[key]["can_select"] or perm.can_select
        agg[key]["can_export"] = agg[key]["can_export"] or perm.can_export
        agg[key]["can_import"] = agg[key]["can_import"] or perm.can_import
        agg[key]["in_sidebar"] = agg[key]["in_sidebar"] or perm.in_sidebar
    return agg


@router.get("/modules", name="get_modules")
async def get_modules():
    """Get all module metadata with labels and icons."""
    return {
        "status": "success",
        "data": {
            "labels": MODULE_LABELS,
            "icons": MODULE_ICONS,
        }
    }


@router.get("", name="get_meta_list")
async def get_meta_list(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """List all entities the user has access to."""
    user: CurrentUser = await get_current_user_from_token(authorization, db)
    
    # Get all entities
    entities = MetaRegistry.list_all()
    
    # Get module orders
    module_orders_result = await db.execute(select(ModuleOrder))
    module_orders = {mo.module_name: mo.sort_order for mo in module_orders_result.scalars().all()}
    
    # Get entity orders
    entity_orders_result = await db.execute(select(EntityOrder))
    entity_orders = {eo.entity_name: eo.sort_order for eo in entity_orders_result.scalars().all()}
    
    # If no user or user is not authenticated, return empty list
    if not user or user.username == "anonymous":
        return {
            "status": "success", 
            "data": []
        }
    
    # If user is SystemManager, return all entities
    if user.is_superuser:
        entity_list = [
            {
                "name": e.name,
                "label": e.label,
                "module": e.module,
                "group": e.group,
                "icon": e.icon,
                "in_sidebar": e.in_sidebar,
                "_module_order": module_orders.get(_module_order_key(e.module), 999),
                "_entity_order": entity_orders.get(e.name, 999),
            }
            for e in entities
        ]
        # Sort by module order, then entity order
        entity_list.sort(key=lambda x: (x["_module_order"], x["_entity_order"]))
        # Remove temporary sort fields
        for e in entity_list:
            del e["_module_order"]
            del e["_entity_order"]
        
        return {
            "status": "success",
            "data": entity_list
        }

    role_ids = user.role_ids

    # Fetch all permissions for user's roles
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id.in_(role_ids))
    )
    permissions = result.scalars().all()
    perms_by_entity = _aggregate_permissions(permissions)

    filtered_entities = []
    for e in entities:
        perms = perms_by_entity.get(
            e.name,
            {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "in_sidebar": False,
            },
        )
        # Only include entities the user can read AND has permission to show in sidebar
        if not perms["can_read"] or not perms["in_sidebar"]:
            continue
        filtered_entities.append(
            {
                "name": e.name,
                "label": e.label,
                "module": e.module,
                "group": e.group,
                "icon": e.icon,
                "in_sidebar": perms["in_sidebar"],
                "_module_order": module_orders.get(_module_order_key(e.module), 999),
                "_entity_order": entity_orders.get(e.name, 999),
            }
        )
    
    # Sort by module order, then entity order
    filtered_entities.sort(key=lambda x: (x["_module_order"], x["_entity_order"]))
    # Remove temporary sort fields
    for e in filtered_entities:
        del e["_module_order"]
        del e["_entity_order"]

    return {
        "status": "success",
        "data": filtered_entities,
    }


@router.get("/{entity}", name="get_meta_detail")
async def get_meta_detail(
    entity: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get metadata for a specific entity, including user permissions and workflow."""
    from app.core.exceptions import ForbiddenError

    meta = MetaRegistry.get(entity)
    if not meta:
        return {
            "status": "error",
            "message": f"Entity '{entity}' not found",
        }

    user: CurrentUser = await get_current_user_from_token(authorization, db)

    # Default permissions (superuser / SystemManager)
    permissions = {
        "can_read": True,
        "can_create": True,
        "can_update": True,
        "can_delete": True,
        "can_select": True,
        "can_export": True,
        "can_import": True,
    }

    # Aggregated permissions for ALL entities the user has access to
    # (needed to filter links and provide link_permissions)
    all_perms_by_entity: dict[str, dict[str, bool]] = {}

    if user and not user.is_superuser:
        role_ids = user.role_ids
        # Fetch ALL permissions for user's roles (not just this entity)
        result = await db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id.in_(role_ids))
        )
        all_perms = result.scalars().all()
        all_perms_by_entity = _aggregate_permissions(all_perms)

        entity_perms = all_perms_by_entity.get(entity)
        if entity_perms:
            permissions = {
                "can_read": entity_perms.get("can_read", False),
                "can_create": entity_perms.get("can_create", False),
                "can_update": entity_perms.get("can_update", False),
                "can_delete": entity_perms.get("can_delete", False),
                "can_select": entity_perms.get("can_select", False),
                "can_export": entity_perms.get("can_export", False),
                "can_import": entity_perms.get("can_import", False),
            }
        else:
            permissions = {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "can_select": False,
                "can_export": False,
                "can_import": False,
            }

    # If user cannot read this entity, return 403
    # Exception: allow authenticated users to access "user" entity metadata for their own profile
    if not permissions["can_read"] and entity != "user":
        raise ForbiddenError(f"You don't have permission to access {meta.label}")

    meta_dict = MetaRegistry.to_dict(meta)
    meta_dict["permissions"] = permissions

    # Filter links: only include linked entities the user can read
    if meta_dict.get("links") and user and not user.is_superuser:
        filtered_links = []
        for link in meta_dict["links"]:
            link_entity = link.get("entity")
            if not link_entity:
                continue
            link_perms = all_perms_by_entity.get(link_entity, {})
            if link_perms.get("can_read", False):
                # Attach permissions for the linked entity so frontend can gate CRUD
                link["permissions"] = {
                    "can_read": link_perms.get("can_read", False),
                    "can_create": link_perms.get("can_create", False),
                    "can_update": link_perms.get("can_update", False),
                    "can_delete": link_perms.get("can_delete", False),
                }
                filtered_links.append(link)
        meta_dict["links"] = filtered_links
    elif meta_dict.get("links") and user and user.is_superuser:
        # Superuser: attach full permissions to all links
        for link in meta_dict["links"]:
            link["permissions"] = {
                "can_read": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }

    # Build link_permissions map for link fields (can_read, can_select per linked entity)
    link_field_permissions: dict[str, dict[str, bool]] = {}
    if meta.fields:
        for field in meta.fields:
            link_entity = getattr(field, 'link_entity', None) or getattr(field, 'child_entity', None)
            if not link_entity or link_entity in link_field_permissions:
                continue
            if user and user.is_superuser:
                link_field_permissions[link_entity] = {"can_read": True, "can_select": True, "can_create": True}
            else:
                lp = all_perms_by_entity.get(link_entity, {})
                link_field_permissions[link_entity] = {
                    "can_read": lp.get("can_read", False),
                    "can_select": lp.get("can_select", False) or lp.get("can_read", False),
                    "can_create": lp.get("can_create", False),
                }
    meta_dict["link_field_permissions"] = link_field_permissions

    # Fetch workflow via repository (DB first, then JSON fallback)
    workflow_repo = WorkflowRepository(db)
    meta_dict["workflow"] = await workflow_repo.build_workflow_meta_dict(
        entity, json_workflow_meta=meta.workflow
    )

    return {
        "status": "success",
        "data": meta_dict,
    }
