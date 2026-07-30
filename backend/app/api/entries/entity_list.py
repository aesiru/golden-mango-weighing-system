"""
Entity List Routes
===================
List operations for entities with smart field filtering.
Thin handlers that delegate to LinkTitleService.
"""
import re
from typing import Any, Optional, Set
from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql.sqltypes import String, Text

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.serialization import record_to_dict
from app.core.exceptions import NotFoundError, ForbiddenError
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.documents.link_title_service import (
    build_link_titles_batch,
    build_link_titles_single,
    inject_link_name_fields,
)

router = APIRouter(tags=["entity"])


def _extract_referenced_fields(meta: Any) -> Set[str]:
    """Extract all field names referenced in conditional logic across all fields.
    
    Parses show_when, editable_when, display_depends_on, mandatory_depends_on,
    list_view_depends_on to find field dependencies.
    """
    referenced: Set[str] = set()
    
    if not meta or not hasattr(meta, "fields"):
        return referenced
    
    for field in meta.fields:
        # Extract from show_when (dict format: {"field_name": [...values]})
        if hasattr(field, "show_when") and field.show_when:
            if isinstance(field.show_when, dict):
                referenced.update(field.show_when.keys())
        
        # Extract from editable_when (dict format)
        if hasattr(field, "editable_when") and field.editable_when:
            if isinstance(field.editable_when, dict):
                referenced.update(field.editable_when.keys())
        
        # Extract from display_depends_on (eval format: "eval:doc.field_name ...")
        if hasattr(field, "display_depends_on") and field.display_depends_on:
            if isinstance(field.display_depends_on, str):
                matches = re.findall(r'doc\.(\w+)', field.display_depends_on)
                referenced.update(matches)
        
        # Extract from mandatory_depends_on (eval format)
        if hasattr(field, "mandatory_depends_on") and field.mandatory_depends_on:
            if isinstance(field.mandatory_depends_on, str):
                matches = re.findall(r'doc\.(\w+)', field.mandatory_depends_on)
                referenced.update(matches)
        
        # Extract from list_view_depends_on (eval format)
        if hasattr(field, "list_view_depends_on") and field.list_view_depends_on:
            if isinstance(field.list_view_depends_on, str):
                matches = re.findall(r'doc\.(\w+)', field.list_view_depends_on)
                referenced.update(matches)
    
    return referenced


def _get_fields_to_return(meta: Any, mode: str, selectable_columns: Set[str]) -> list[str]:
    """Determine which fields to return based on mode.
    
    Args:
        meta: Entity metadata
        mode: "smart" or "all"
        selectable_columns: Available columns in the database table
    
    Returns:
        List of field names to include in response
    """
    system_fields = {"id", "created_at", "updated_at"}
    
    if mode == "all":
        return list(selectable_columns)
    
    if mode == "smart":
        referenced_fields = _extract_referenced_fields(meta)
        fields_to_return: Set[str] = set()

        if meta and hasattr(meta, "fields"):
            for field in meta.fields:
                field_name = field.name if hasattr(field, "name") else None
                if field_name:
                    # Include if in_list_view=true OR required=true OR referenced in conditions
                    in_list_view = getattr(field, "in_list_view", False)
                    required = getattr(field, "required", False)
                    if in_list_view or required or field_name in referenced_fields:
                        fields_to_return.add(field_name)

        # Always include system fields
        fields_to_return.update(system_fields & selectable_columns)

        # Only return fields that actually exist in the table
        return [f for f in fields_to_return if f in selectable_columns]
    
    # Default to all for unknown modes
    return list(selectable_columns)


def _record_to_dict_filtered(record: Any, fields: list[str]) -> dict:
    """Convert record to dict, filtering to only include specified fields."""
    full_dict = record_to_dict(record)
    return {k: v for k, v in full_dict.items() if k in fields}


@router.get("/{entity}/list", name="get_entity_list")
async def get_entity_list(
    entity: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    filter_field: Optional[str] = Query(None),
    filter_value: Optional[str] = Query(None),
    enrich_links: bool = Query(True),
    fields: str = Query("smart", pattern="^(smart|all)$"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """List records for an entity with optional link enrichment and field filtering.
    
    Args:
        entity: Entity name
        page: Page number (1-indexed)
        page_size: Number of records per page
        sort_field: Field to sort by
        sort_order: Sort direction (asc or desc)
        filter_field: Field to filter on
        filter_value: Filter value
        enrich_links: Whether to fetch and inject link field display names
        fields: Field mode - "smart" (in_list_view + condition refs) or "all"
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to access {meta.label}")

    model = get_entity_model(entity)
    if not model:
        return ActionResponse(status="error", message=f"Model for '{entity}' not found")

    offset = (page - 1) * page_size
    selectable_columns = set(getattr(model, "__table__").columns.keys())
    
    # Determine which fields to return based on mode
    fields_to_return = _get_fields_to_return(meta, fields, selectable_columns)

    query = select(model)
    count_query = select(func.count()).select_from(model)

    if filter_field and filter_value is not None:
        if filter_field not in selectable_columns:
            return ActionResponse(status="error", message=f"Invalid filter field '{filter_field}'")
        col = getattr(model, filter_field)
        if isinstance(col.type, (String, Text)):
            clause = col.ilike(f"%{filter_value}%")
        else:
            clause = col == filter_value
        query = query.where(clause)
        count_query = count_query.where(clause)

    if sort_field:
        if sort_field not in selectable_columns:
            return ActionResponse(status="error", message=f"Invalid sort field '{sort_field}'")
        sort_col = getattr(model, sort_field)
        query = query.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())
    elif hasattr(model, 'updated_at'):
        query = query.order_by(model.updated_at.desc())
    elif hasattr(model, 'created_at'):
        query = query.order_by(model.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    result = await db.execute(query.offset(offset).limit(page_size))
    records = result.scalars().all()

    # Convert records to dicts with field filtering
    data = [_record_to_dict_filtered(r, fields_to_return) for r in records]
    
    # Enrich with link titles if requested
    if enrich_links and data:
        records_dict = data
        all_link_titles = await build_link_titles_batch(db, meta, records_dict)
        for i, record_dict in enumerate(records_dict):
            record_dict["_link_titles"] = all_link_titles[i] or {}
            inject_link_name_fields(meta, record_dict, record_dict["_link_titles"])

    return {
        "status": "success",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/{entity}/detail/{id}", name="get_entity_detail")
async def get_entity_detail(
    entity: str,
    id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Get a single record by ID."""
    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to read {meta.label}")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    result = await db.execute(select(model).where(model.id == id))
    record = result.scalar_one_or_none()

    if not record:
        raise NotFoundError(meta.label, id)

    record_data = record_to_dict(record)

    # Get linked entity counts
    linked_counts = {}
    if meta.links:
        for link in meta.links:
            link_entity = link.get("entity")
            fk_field = link.get("fk_field")
            if link_entity and fk_field:
                link_model = get_entity_model(link_entity)
                if link_model and hasattr(link_model, fk_field):
                    count_stmt = select(func.count()).select_from(link_model).where(
                        getattr(link_model, fk_field) == record.id
                    )
                    count_result = await db.execute(count_stmt)
                    linked_counts[link_entity] = count_result.scalar() or 0

    # Build _link_titles for link fields
    link_titles = await build_link_titles_single(db, meta, record)

    inject_link_name_fields(meta, record_data, link_titles)

    return {
        "status": "success",
        "data": record_data,
        "linked_counts": linked_counts,
        "_link_titles": link_titles,
    }


@router.get("/{entity}/schema", name="get_entity_schema")
async def get_entity_schema(
    entity: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """
    Return the JSON Schema for the entity's write and read Pydantic models.

    Clients (frontend, integrations) can use this to:
    - Understand required vs optional fields
    - Determine field types for dynamic form rendering
    - Validate payloads client-side before submitting

    Requires ``read`` permission on the entity.
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    ):
        raise ForbiddenError(f"You don't have permission to access {meta.label}")

    write_schema = MetaRegistry.get_write_schema(entity)
    read_schema = MetaRegistry.get_read_schema(entity)

    return {
        "status": "success",
        "entity": entity,
        "label": meta.label,
        "module": meta.module,
        "write_schema": write_schema.model_json_schema() if write_schema else None,
        "read_schema": read_schema.model_json_schema() if read_schema else None,
    }
