"""
Users Router
============
User display name resolution for created_by/last_modified_by fields.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.framework.models.auth import User

router = APIRouter(prefix="/system/users", tags=["system-users"])


@router.get("/resolve-display-names")
async def resolve_user_display_names(
    user_ids: str = Query(..., description="Comma-separated list of user IDs to resolve"),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve user IDs to display names (full_name or username).

    Used for displaying created_by and last_modified_by fields in the UI.

    Query param: user_ids - comma-separated list of user IDs (e.g., "usr-001,usr-002")

    Returns: {user_id: display_name} mapping
    """
    # Parse user IDs
    ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    if not ids:
        return {"status": "success", "data": {}}
    
    # Batch fetch users
    result = await db.execute(select(User).where(User.id.in_(ids)))
    users = result.scalars().all()
    
    # Build display name mapping
    display_names = {}
    for user in users:
        # Use full_name if available, fallback to username
        display_name = user.full_name if user.full_name else user.username
        display_names[user.id] = display_name
    
    # For any IDs not found, return the ID itself
    for uid in ids:
        if uid not in display_names:
            display_names[uid] = uid
    
    return {
        "status": "success",
        "data": display_names
    }
