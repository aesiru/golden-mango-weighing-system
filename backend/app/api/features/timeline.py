"""
Timeline Feature
================
Unified activity feed per entity record, combining audit log, comments,
workflow transitions, and attachments into a single chronological view.

    GET /timeline/{entity}/{record_id}   — ordered activity feed for a record
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.infrastructure import AuditLog, Comment, Attachment
from app.core.security import CurrentUser, require_authenticated_user
from app.meta.registry import MetaRegistry
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service

router = APIRouter(prefix="/timeline", tags=["timeline"])


def _audit_event(row: AuditLog) -> dict:
    return {
        "type": "audit",
        "action": row.action,
        "user_id": row.user_id,
        "username": row.username,
        "changed_fields": json.loads(row.changed_fields) if row.changed_fields else [],
        "timestamp": row.created_at.isoformat() if row.created_at else None,
    }


def _comment_event(row: Comment) -> dict:
    return {
        "type": "comment",
        "id": row.id,
        "body": row.body,
        "author_id": row.author_id,
        "username": row.author_username,
        "is_edited": row.is_edited,
        "parent_id": row.parent_id,
        "timestamp": row.created_at.isoformat() if row.created_at else None,
    }


def _attachment_event(row: Attachment) -> dict:
    return {
        "type": "attachment",
        "id": row.id,
        "file_name": row.original_name,
        "file_size": row.file_size,
        "mime_type": row.mime_type,
        "username": row.uploaded_by,
        "timestamp": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/{entity}/{record_id}", name="get_timeline")
async def get_timeline(
    entity: str,
    record_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Unified chronological activity feed for a specific record."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return {"status": "error", "message": f"Entity '{entity}' not found"}

    if not await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser
    ):
        return {"status": "error", "message": "Permission denied"}

    events: list[dict] = []

    # Audit events
    audit_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_name == entity, AuditLog.record_id == record_id)
        .order_by(AuditLog.created_at.desc())
        .limit(page_size * 3)  # fetch extra since we merge & re-sort
    )
    for row in audit_res.scalars().all():
        events.append(_audit_event(row))

    # Comment events
    comment_res = await db.execute(
        select(Comment)
        .where(Comment.entity_name == entity, Comment.record_id == record_id)
        .order_by(Comment.created_at.desc())
        .limit(page_size * 3)
    )
    for row in comment_res.scalars().all():
        events.append(_comment_event(row))

    # Attachment events
    attach_res = await db.execute(
        select(Attachment)
        .where(Attachment.entity_name == entity, Attachment.record_id == record_id)
        .order_by(Attachment.created_at.desc())
        .limit(page_size * 3)
    )
    for row in attach_res.scalars().all():
        events.append(_attachment_event(row))

    # Sort all events newest-first
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)

    total = len(events)
    offset = (page - 1) * page_size
    page_data = events[offset: offset + page_size]

    return {
        "status": "success",
        "entity": entity,
        "record_id": record_id,
        "data": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
