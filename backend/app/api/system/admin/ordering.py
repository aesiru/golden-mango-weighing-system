"""
Ordering Router
===============
Module and entity ordering endpoints.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.ordering import ModuleOrder, EntityOrder
from app.meta.registry import MetaRegistry
from app.api.system.meta import _module_order_key
from app.application.services.notifications.socketio import socket_manager
from .common import api_response

router = APIRouter(tags=["admin-ordering"])


@router.put("/ordering/modules")
async def update_module_order(
    order_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update the display order of modules."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    modules = order_data.get("modules", [])
    
    for idx, module_name in enumerate(modules):
        order_key = _module_order_key(module_name)
        result = await db.execute(
            select(ModuleOrder).where(ModuleOrder.module_name == order_key)
        )
        module_order = result.scalar_one_or_none()
        
        if module_order:
            module_order.sort_order = idx
        else:
            module_order = ModuleOrder(
                module_name=order_key,
                sort_order=idx
            )
            db.add(module_order)
    
    await db.commit()
    
    return api_response(
        status="success",
        message="Module order updated successfully"
    )


@router.get("/ordering/entities")
async def get_module_entities(
    module: str = Query(..., description="Module name to get entities for"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get entities for a specific module with their current order."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    all_entities = MetaRegistry.list_all()
    module_entities = [e for e in all_entities if _module_order_key(e.module) == _module_order_key(module)]
    
    module_order_key = _module_order_key(module)
    entity_orders_result = await db.execute(
        select(EntityOrder).where(EntityOrder.module_name == module_order_key)
    )
    entity_orders = {eo.entity_name: eo.sort_order for eo in entity_orders_result.scalars().all()}
    
    entities_data = []
    for entity in module_entities:
        entities_data.append({
            "name": entity.name,
            "label": entity.label,
            "module": entity.module,
            "sort_order": entity_orders.get(entity.name, 999),
        })
    
    entities_data.sort(key=lambda x: x["sort_order"])
    
    return api_response(
        status="success",
        message="Module entities retrieved successfully",
        data=entities_data
    )


@router.put("/ordering/entities")
async def update_entity_order(
    order_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update the display order of entities within a module."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    # Check if this is the new module-scoped format
    if "module" in order_data and "entity_names" in order_data:
        module_name = order_data.get("module")
        entity_names = order_data.get("entity_names", [])
        module_order_key = _module_order_key(module_name)
        
        all_entities = MetaRegistry.list_all()
        module_entities = {e.name: e for e in all_entities if _module_order_key(e.module) == module_order_key}
        
        if not module_entities:
            return api_response(
                status="error",
                message=f"Module '{module_name}' not found"
            )
        
        for entity_name in entity_names:
            if entity_name not in module_entities:
                return api_response(
                    status="error",
                    message=f"Entity '{entity_name}' does not belong to module '{module_name}'"
                )
        
        for idx, entity_name in enumerate(entity_names):
            result = await db.execute(
                select(EntityOrder).where(EntityOrder.entity_name == entity_name)
            )
            entity_order = result.scalar_one_or_none()
            
            if entity_order:
                entity_order.sort_order = idx
                entity_order.module_name = module_order_key
            else:
                entity_order = EntityOrder(
                    entity_name=entity_name,
                    module_name=module_order_key,
                    sort_order=idx
                )
                db.add(entity_order)
        
        await db.commit()

        await socket_manager.emit_meta_change(
            "ordering:entities",
            {"module": module_name, "entity_names": entity_names}
        )
        
        return api_response(
            status="success",
            message="Entity order updated successfully"
        )
    
    # Legacy format: { entities: [{name, module, sort_order}] }
    entities = order_data.get("entities", [])
    
    for entity_data in entities:
        entity_name = entity_data.get("name")
        module_name = entity_data.get("module")
        module_order_key = _module_order_key(module_name)
        sort_order = entity_data.get("sort_order", 0)
        
        result = await db.execute(
            select(EntityOrder).where(EntityOrder.entity_name == entity_name)
        )
        entity_order = result.scalar_one_or_none()
        
        if entity_order:
            entity_order.sort_order = sort_order
            entity_order.module_name = module_order_key
        else:
            entity_order = EntityOrder(
                entity_name=entity_name,
                module_name=module_order_key,
                sort_order=sort_order
            )
            db.add(entity_order)
    
    await db.commit()

    await socket_manager.emit_meta_change(
        "ordering:entities",
        {"entities": entities}
    )
    
    return api_response(
        status="success",
        message="Entity order updated successfully"
    )
