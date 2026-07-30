"""
Entity Options Routes
======================
Options and grouped-options for link field dropdowns.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.sql.sqltypes import String, Text

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.meta.registry import MetaRegistry
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.infrastructure.database.query.filter_builder import build_filter_condition

router = APIRouter(tags=["entity"])


@router.get("/{child_entity}/grouped-options", name="get_grouped_options")
async def get_grouped_options(
    child_entity: str,
    parent_entity: str = Query(...),
    child_parent_fk_field: str = Query(...),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Get options grouped by parent for parent_child_link field type."""
    child_meta = MetaRegistry.get(child_entity)
    parent_meta = MetaRegistry.get(parent_entity)

    if not child_meta:
        return {"status": "error", "message": f"Child entity '{child_entity}' not found"}
    if not parent_meta:
        return {"status": "error", "message": f"Parent entity '{parent_entity}' not found"}

    user = await get_current_user_from_token(authorization, db)
    # Allow access if user has can_select OR can_read permission
    has_select = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="select",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_read = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not has_select and not has_read:
        return {"status": "error", "message": "Permission denied"}

    child_model = get_entity_model(child_entity)
    parent_model = get_entity_model(parent_entity)

    if not child_model or not parent_model:
        return {"status": "error", "message": "Model not found"}

    child_value_field = "id"
    child_label_field = child_meta.title_field or "name"
    parent_value_field = "id"
    parent_label_field = parent_meta.title_field or "name"

    query = select(child_model, parent_model).join(
        parent_model,
        getattr(child_model, child_parent_fk_field) == parent_model.id
    )

    if search and hasattr(child_model, child_label_field):
        query = query.where(getattr(child_model, child_label_field).ilike(f"%{search}%"))

    if hasattr(parent_model, parent_label_field):
        query = query.order_by(getattr(parent_model, parent_label_field))
    if hasattr(child_model, child_label_field):
        query = query.order_by(getattr(child_model, child_label_field))

    query = query.limit(limit)

    result = await db.execute(query)
    rows = result.all()

    groups_dict = {}
    for child_record, parent_record in rows:
        parent_value = getattr(parent_record, parent_value_field, None)
        parent_label = getattr(parent_record, parent_label_field, None) or parent_value
        parent_key = str(parent_value)

        if parent_key not in groups_dict:
            groups_dict[parent_key] = {"label": str(parent_label), "options": []}

        child_value = getattr(child_record, child_value_field, None)
        child_label = getattr(child_record, child_label_field, None) or child_value

        option = {"value": str(child_value), "label": str(child_label)}

        # Add description using child entity's list_view fields
        child_list_view_fields = [field.name for field in child_meta.fields if field.in_list_view and field.name != child_label_field]
        if child_list_view_fields:
            description_parts = []
            for field_name in child_list_view_fields:
                if hasattr(child_record, field_name):
                    field_value = getattr(child_record, field_name)
                    if field_value not in (None, ""):
                        description_parts.append(str(field_value))
            if description_parts:
                option["description"] = " | ".join(description_parts)

        groups_dict[parent_key]["options"].append(option)

    return {"status": "success", "groups": list(groups_dict.values())}


@router.get("/{entity}/options", name="get_entity_options")
async def get_entity_options(
    entity: str,
    search: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=500),
    filters: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Get options for link field (combo box/select)."""
    debug_entity = False
    if debug_entity:
        print("[entity_options] request", {
            "entity": entity,
            "search": search,
            "limit": limit,
            "filters": filters,
        })
    meta = MetaRegistry.get(entity)
    if not meta:
        return {"status": "error", "message": f"Entity '{entity}' not found", "options": []}

    user = await get_current_user_from_token(authorization, db)
    # Allow access if user has can_select OR can_read permission
    has_select = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="select",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_read = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not has_select and not has_read:
        return {"status": "error", "message": "Permission denied", "options": []}

    model = get_entity_model(entity)
    if not model:
        return {"status": "error", "message": f"Model for '{entity}' not found", "options": []}

    value_field = meta.naming.field if meta.naming and meta.naming.field else "id"
    label_field = meta.title_field or value_field

    query = select(model)

    if search:
        search_cols = []
        
        # Always search value_field and label_field if they exist and are string/text
        if hasattr(model, value_field):
            col = getattr(model, value_field)
            if isinstance(col.type, (String, Text)):
                search_cols.append(col.ilike(f"%{search}%"))
        if hasattr(model, label_field) and label_field != value_field:
            col = getattr(model, label_field)
            if isinstance(col.type, (String, Text)):
                search_cols.append(col.ilike(f"%{search}%"))
        
        # Also search in entity's search_fields if defined
        if meta.search_fields:
            for field_name in meta.search_fields:
                if hasattr(model, field_name) and field_name not in (value_field, label_field):
                    col = getattr(model, field_name)
                    if isinstance(col.type, (String, Text)):
                        search_cols.append(col.ilike(f"%{search}%"))
        
        if search_cols:
            query = query.where(or_(*search_cols))

    # Default ordering:
    # - If search is empty: show most recently created records first (better UX for lookups)
    # - If search is provided: keep deterministic label ordering
    if not search and hasattr(model, "created_at"):
        query = query.order_by(desc(getattr(model, "created_at")))
    elif hasattr(model, label_field):
        query = query.order_by(getattr(model, label_field))

    # Apply filters (JSON-encoded dict of field_name: value)
    if filters:
        import json
        try:
            filter_dict = json.loads(filters)
            for field_name, field_value in filter_dict.items():
                if hasattr(model, field_name) and field_value is not None:
                    condition = build_filter_condition(getattr(model, field_name), field_value)
                    if condition is not None:
                        query = query.where(condition)
        except (json.JSONDecodeError, TypeError):
            pass

    query = query.limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    if debug_entity:
        print("[entity_options] records", {
            "entity": entity,
            "count": len(records),
            "ids": [getattr(record, "id", None) for record in records[:10]],
        })

    options = []
    # Use fields marked as in_options_description for dropdown description;
    # fall back to in_list_view for backward compatibility.
    desc_fields = [f for f in meta.fields if f.in_options_description and f.name != label_field]
    if not desc_fields:
        desc_fields = [f for f in meta.fields if f.in_list_view and f.name != label_field]

    # Cache for linked titles to avoid repeat queries: {entity: {id: title}}
    link_title_cache: dict[str, dict[str, str]] = {}

    async def _resolve_link_title(link_entity: str, record_id: Any) -> str:
        if record_id in (None, ""):
            return str(record_id)
        cache = link_title_cache.setdefault(link_entity, {})
        key = str(record_id)
        if key in cache:
            return cache[key]
        link_meta = MetaRegistry.get(link_entity)
        link_model = get_entity_model(link_entity)
        if not link_meta or not link_model:
            cache[key] = key
            return key
        title_field = link_meta.title_field or "id"
        result = await db.execute(select(getattr(link_model, title_field)).where(link_model.id == record_id))
        title_val = result.scalar_one_or_none()
        cache[key] = str(title_val or key)
        return cache[key]

    # Precompute label field meta (to detect link labels)
    label_field_meta = next((f for f in meta.fields if f.name == label_field), None)

    for record in records:
        value = getattr(record, value_field, None) or getattr(record, "id", None)
        label_raw = getattr(record, label_field, None) or value

        # If the label field itself is a link, resolve to its title_field
        if label_field_meta and label_field_meta.link_entity:
            label_resolved = await _resolve_link_title(label_field_meta.link_entity, label_raw)
        else:
            label_resolved = label_raw

        option = {"value": str(value), "label": str(label_resolved)}

        # Add description using list_view fields
        if desc_fields:
            description_parts = []
            for field_meta in desc_fields:
                field_name = field_meta.name
                if hasattr(record, field_name):
                    field_value = getattr(record, field_name)
                    if field_value in (None, ""):
                        continue
                    # If this field is a link, resolve its title_field
                    if field_meta.link_entity:
                        field_value = await _resolve_link_title(field_meta.link_entity, field_value)
                    description_parts.append(str(field_value))
            if description_parts:
                option["description"] = " | ".join(description_parts)

        options.append(option)

    if debug_entity:
        print("[entity_options] response", {
            "entity": entity,
            "option_count": len(options),
            "options": options[:10],
        })

    return {"status": "success", "options": options}


@router.post("/query-options", name="post_query_options")
async def post_query_options(
    request: dict,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Execute a whitelisted query for query_link field type."""
    from app.application.services.documents.query_link import execute_query_link

    key = request.get("key")
    entity = request.get("entity")
    field = request.get("field")
    form_state = request.get("form_state")
    static_params = request.get("static_params")

    if not key:
        return {"status": "error", "message": "Query key is required", "options": []}
    if not entity:
        return {"status": "error", "message": "Entity is required", "options": []}

    user = await get_current_user_from_token(authorization, db)
    
    # For now, allow request_activity_type queries without strict permission check
    # TODO: Fix entity registration for request_activity_type
    if key != "request_activity_type":
        meta = MetaRegistry.get(entity)
        if meta and not await rbac.check_permission(
            user_id=user.id,
            entity=entity,
            action="read",
            role_ids=user.role_ids,
            is_superuser=user.is_superuser
        ):
            return {"status": "error", "message": "Permission denied", "options": []}

    result = await execute_query_link(
        key=key, db=db, entity=entity, field=field or "",
        form_state=form_state, static_params=static_params
    )
    return result
