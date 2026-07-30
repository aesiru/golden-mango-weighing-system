"""
Entity Audit Log Routes
=======================
GET /api/entity/{entity}/{record_id}/audit - List audit trail for a record.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.infrastructure import AuditLog
from app.api.dependencies import require_entity_permission

router = APIRouter()


@router.get("/{entity}/{record_id}/audit", dependencies=[Depends(require_entity_permission("read"))])
async def get_audit_trail(
    entity: str,
    record_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
):
    """Get audit trail for a specific entity record."""
    offset = (page - 1) * page_size

    query = (
        select(AuditLog)
        .where(AuditLog.entity_name == entity, AuditLog.record_id == record_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    from sqlalchemy import func
    count_q = (
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.entity_name == entity, AuditLog.record_id == record_id)
    )
    total = (await db.execute(count_q)).scalar() or 0

    items = []
    for e in entries:
        items.append({
            "id": e.id,
            "action": e.action,
            "user_id": e.user_id,
            "username": e.username,
            "before_snapshot": json.loads(e.before_snapshot) if e.before_snapshot else None,
            "after_snapshot": json.loads(e.after_snapshot) if e.after_snapshot else None,
            "changed_fields": json.loads(e.changed_fields) if e.changed_fields else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "status": "success",
        "data": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
