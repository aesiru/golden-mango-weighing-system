"""
System Audit Log
================
System-wide audit event viewer for admins.  All writes to this log are
performed by app.services.audit via lifecycle hooks — this route is read-only.

    GET /audit-log               — paginated event list (filters: entity, user, action, date range)
    GET /audit-log/{id}          — single event detail with before/after snapshots
"""
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.infrastructure import AuditLog
from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/audit-log", tags=["system"])

_PAGE_SIZE_LIMIT = 200


def _serialize(row: AuditLog) -> dict:
    return {
        "id": row.id,
        "entity_name": row.entity_name,
        "record_id": row.record_id,
        "action": row.action,
        "user_id": row.user_id,
        "username": row.username,
        "changed_fields": json.loads(row.changed_fields) if row.changed_fields else [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _require_admin(current_user: CurrentUser) -> None:
    if not current_user.is_superuser and "Administrator" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("", name="list_audit_log")
async def list_audit_log(
    entity: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    record_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=_PAGE_SIZE_LIMIT),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated audit log viewer (admin-only)."""
    _require_admin(current_user)

    filters = []
    if entity:
        filters.append(AuditLog.entity_name == entity)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if record_id:
        filters.append(AuditLog.record_id == record_id)
    if date_from:
        from datetime import datetime
        filters.append(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        from datetime import datetime
        filters.append(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    offset = (page - 1) * page_size
    q = (
        select(AuditLog)
        .where(and_(*filters) if filters else True)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    rows = result.scalars().all()

    return {
        "status": "success",
        "data": [_serialize(r) for r in rows],
        "page": page,
        "page_size": page_size,
    }


@router.get("/{log_id}", name="get_audit_log_entry")
async def get_audit_log_entry(
    log_id: int,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single audit log entry with full before/after snapshots."""
    _require_admin(current_user)

    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")

    detail = _serialize(row)
    detail["before_snapshot"] = json.loads(row.before_snapshot) if row.before_snapshot else None
    detail["after_snapshot"] = json.loads(row.after_snapshot) if row.after_snapshot else None
    return {"status": "success", "data": detail}
