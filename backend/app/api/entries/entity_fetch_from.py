"""
Entity Fetch-From Routes
========================
Lightweight endpoint that returns only the specific fields needed
for declarative fetch_from autofill rules.

GET /api/entity/{entity}/fetch_from/{id}?fields=field_a,field_b

Returns:
    {
        "status": "success",
        "data": { "field_a": "val", "field_b": "val" },
        "_link_titles": { "entity_name::id_val": "Display Name" }
    }

This avoids fetching the full entity detail document when only a
small subset of fields is required for autofill.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.schemas.base import ActionResponse
from app.api.dependencies import get_fetch_from_service, require_entity_permission
from app.application.services.fetch_from_service import FetchFromService

router = APIRouter(tags=["entity"])


@router.get("/{entity}/fetch_from/{record_id}", dependencies=[Depends(require_entity_permission("read"))])
async def get_fetch_from_fields(
    entity: str,
    record_id: str,
    fields: str = Query(..., description="Comma-separated list of field names to return"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    service: FetchFromService = Depends(get_fetch_from_service),
):
    """
    Return only the requested fields from a linked record plus display
    titles for any link fields among them.

    Called by the frontend useFetchFrom composable when a source link
    field changes. Much lighter than GET /entity/detail/{id} because it:
      1. Selects only the requested columns from the DB.
      2. Resolves display titles only for those link fields.
    """
    # Auth — any authenticated user may read linked record fields for autofill.
    await get_current_user_from_token(authorization, db)

    requested_fields = [f.strip() for f in fields.split(",") if f.strip()]
    if not requested_fields:
        return ActionResponse(status="error", message="'fields' query param must not be empty")

    data, link_titles = await service.get_fetch_from_fields(entity, record_id, requested_fields)
    if data is None:
        return ActionResponse(status="error", message="Record not found")

    return {
        "status": "success",
        "data": data,
        "_link_titles": link_titles,
    }
