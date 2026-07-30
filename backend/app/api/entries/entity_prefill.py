"""
Entity Prefill Routes
======================
Returns default field values for new records.
Called by the frontend on /new pages to pre-populate date fields, etc.

Entity JSON can define a "prefill" section:
    "prefill": {
        "date_requested": "today",
        "requested_date": "today"
    }

Supported values:
    "today"  → current date (YYYY-MM-DD)
    "now"    → current datetime (ISO format)
    any str  → literal value
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.services.documents.link_title_service import build_link_titles_for_record
from app.core.security import get_current_user_from_token, CurrentUser
from app.meta.registry import MetaRegistry

router = APIRouter(tags=["entity-prefill"])

# Mapping of magic tokens to callables
_PREFILL_RESOLVERS = {
    "today": lambda: str(date.today()),
    "now": lambda: datetime.now().isoformat(),
}


@router.get("/{entity}/prefill")
async def get_entity_prefill(
    entity: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return pre-fill values for a new record of the given entity.

    Reads the "prefill" key from the entity JSON metadata and resolves
    dynamic tokens like "today" and "now" to actual values.

    Foreign-key prefills from query params are handled separately by the
    frontend and are NOT changed here.
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        return {"status": "error", "message": f"Entity '{entity}' not found", "data": {}}

    current_user = await get_current_user_from_token(authorization, db)

    # Get prefill rules from entity metadata
    prefill_rules = meta.prefill or {}

    # Resolve dynamic values
    resolved = {}
    for field_name, value in prefill_rules.items():
        if isinstance(value, str) and value.lower() in _PREFILL_RESOLVERS:
            resolved[field_name] = _PREFILL_RESOLVERS[value.lower()]()
        else:
            resolved[field_name] = value

    # All module-specific entity prefill logic removed
    # Only core framework entities remain
    # Future modules can add their own prefill logic

    link_titles = await build_link_titles_for_record(meta, resolved, db)
    return {"status": "success", "data": resolved, "_link_titles": link_titles}
