"""
Global Search
=============
Cross-entity full-text search across all entities that support it.
Searches entity records by querying their document service.

    GET /search?q={query}&entity={filter}&page={n}&page_size={n}
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_authenticated_user
from app.meta.registry import MetaRegistry
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service

router = APIRouter(prefix="/search", tags=["search"])

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


@router.get("", name="global_search")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    entity: Optional[str] = Query(None, description="Limit search to a specific entity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Full-text search across all accessible entities."""
    from app.application.services.documents.document import get_list

    # Determine which entities to search
    all_meta = MetaRegistry.list_all()
    searchable = [m for m in all_meta if m.searchable if True] if all_meta else []

    if entity:
        searchable = [m for m in (all_meta or []) if m.name == entity]

    results: list[dict] = []
    for meta in (searchable or []):
        # Respect RBAC — skip entities the user can't read
        if not await rbac.check_permission(
            user_id=current_user.id,
            entity=meta.name,
            action="read",
            role_ids=current_user.role_ids,
            is_superuser=current_user.is_superuser
        ):
            continue

        try:
            # Use get_list with a simple search filter
            # Note: This is a basic implementation - full-text search would require more complex query logic
            rows = await get_list(
                meta.name,
                db=db,
                limit=page_size,
            )
            # Filter rows client-side for the query string (temporary solution)
            for row in rows:
                row_str = str(row).lower()
                if q.lower() in row_str:
                    results.append({
                        "entity": meta.name,
                        "entity_label": meta.label,
                        "id": row.get("id") or row.get("name"),
                        "label": row.get("name") or row.get("title") or row.get("id"),
                        "data": row,
                    })
                if len(results) >= page_size:
                    break
        except Exception:  # noqa: BLE001
            # Skip entities whose search fails (e.g. no full-text support)
            continue

    total = len(results)
    offset = (page - 1) * page_size
    page_data = results[offset: offset + page_size]

    return {
        "status": "success",
        "query": q,
        "data": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
