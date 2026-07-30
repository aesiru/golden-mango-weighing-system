"""
System Attachments
==================
Authoritative upload/download/delete/list routes for file attachments.
This module owns all attachment logic; entity_attachments.py is a thin
context-resolver that delegates here after validating entity + record context.

Route contract:
    POST   /attachments/{entity}/{record_id}                   — upload
    GET    /attachments/{entity}/{record_id}                   — list
    GET    /attachments/{entity}/{record_id}/{id}/download     — binary download
    GET    /attachments/{entity}/{record_id}/{id}/view         — inline view
    DELETE /attachments/{entity}/{record_id}/{id}              — delete

All routes require a valid Bearer token.  Read permission is required for
list/download/view; update permission is required for upload/delete.
"""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.framework.models.infrastructure import Attachment
from app.core.security import get_current_user_from_token
from app.infrastructure.storage import StorageBackend, get_storage
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service

router = APIRouter(prefix="/attachments", tags=["attachments"])

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_attachment_config(entity_name: str):
    """Return attachment config for *entity_name*, or None if attachments are disabled."""
    meta = MetaRegistry.get(entity_name)
    if not meta:
        return None
    config = meta.attachment_config
    if not config or not config.allow_attachments:
        return None
    return config


def _is_own_user_record(entity: str, record_id: str, user) -> bool:
    return bool(user and user.id not in {"anonymous", "unknown"}) and entity == "user" and record_id == user.id


async def _resolve_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    auth_header: Optional[str],
    db: AsyncSession,
    rbac: RBACAppService,
) -> tuple[Attachment, Path] | ActionResponse:
    """Fetch + authorise an attachment; return (model, path) or an error ActionResponse."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(auth_header, db)
    can_read = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not can_read and not _is_own_user_record(entity, record_id, user):
        return ActionResponse(status="error", message="Permission denied")

    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.entity_name == entity,
            Attachment.record_id == record_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return ActionResponse(status="error", message="Attachment not found")

    file_path = Path(attachment.file_path)
    if not file_path.exists():
        return ActionResponse(status="error", message="File not found on disk")

    return attachment, file_path


def _serialize(a: Attachment) -> dict:
    return {
        "id": a.id,
        "file_name": a.original_name,
        "file_size": a.file_size,
        "mime_type": a.mime_type,
        "uploaded_by": a.uploaded_by,
        "description": a.description,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/{entity}/{record_id}", name="system_list_attachments")
async def list_attachments(
    entity: str,
    record_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """List all attachments for the given entity record."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    can_read = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not can_read and not _is_own_user_record(entity, record_id, user):
        return ActionResponse(status="error", message="Permission denied")

    result = await db.execute(
        select(Attachment)
        .where(Attachment.entity_name == entity, Attachment.record_id == record_id)
        .order_by(Attachment.created_at.desc())
    )
    rows = result.scalars().all()
    data = [_serialize(a) for a in rows]
    return {"status": "success", "data": data, "total": len(data)}


@router.post("/{entity}/{record_id}", name="system_upload_attachment")
async def upload_attachment(
    entity: str,
    record_id: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Upload a file attachment to the given entity record."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    can_update = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not can_update and not _is_own_user_record(entity, record_id, user):
        return ActionResponse(status="error", message="Permission denied")

    config = _get_attachment_config(entity)
    if not config:
        return ActionResponse(
            status="error",
            message=f"Attachments are not enabled for '{meta.label}'",
        )

    # Enforce max attachments per record
    count_result = await db.execute(
        select(func.count())
        .select_from(Attachment)
        .where(Attachment.entity_name == entity, Attachment.record_id == record_id)
    )
    current_count = count_result.scalar() or 0
    if current_count >= config.max_attachments:
        return ActionResponse(
            status="error",
            message=f"Maximum attachments ({config.max_attachments}) reached",
        )

    # Validate extension
    original_name = file.filename or "unnamed"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if config.allowed_extensions and ext not in config.allowed_extensions:
        return ActionResponse(
            status="error",
            message=f"File type '.{ext}' not allowed. Allowed: {', '.join(config.allowed_extensions)}",
        )

    content = await file.read()
    file_size = len(content)

    # Validate size
    max_bytes = config.max_file_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return ActionResponse(
            status="error",
            message=f"File too large ({file_size / 1024 / 1024:.1f} MB). Max: {config.max_file_size_mb} MB",
        )

    mime_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

    stored = await storage.save(
        content=content,
        original_name=original_name,
        entity=entity,
        record_id=record_id,
        mime_type=mime_type,
    )

    attachment = Attachment(
        id=stored.file_id,
        entity_name=entity,
        record_id=record_id,
        file_name=stored.stored_name,
        original_name=original_name,
        file_path=stored.file_path,
        file_size=stored.file_size,
        mime_type=stored.mime_type,
        uploaded_by=user.username if user else None,
        description=description,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return ActionResponse(
        status="success",
        message="File uploaded successfully",
        data=_serialize(attachment),
    )


@router.get("/{entity}/{record_id}/{attachment_id}/download", name="system_download_attachment")
async def download_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Download a specific attachment as a file."""
    auth_header = authorization or (f"Bearer {token}" if token else None)
    result = await _resolve_attachment(entity, record_id, attachment_id, auth_header, db, rbac)
    if isinstance(result, ActionResponse):
        return result

    attachment, file_path = result
    return FileResponse(
        path=str(file_path),
        filename=attachment.original_name,
        media_type=attachment.mime_type or "application/octet-stream",
    )


@router.get("/{entity}/{record_id}/{attachment_id}/view", name="system_view_attachment")
async def view_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Serve a specific attachment inline (for browser/canvas rendering)."""
    auth_header = authorization or (f"Bearer {token}" if token else None)
    result = await _resolve_attachment(entity, record_id, attachment_id, auth_header, db, rbac)
    if isinstance(result, ActionResponse):
        return result

    attachment, file_path = result
    return FileResponse(
        path=str(file_path),
        filename=attachment.original_name,
        media_type=attachment.mime_type or "application/octet-stream",
        content_disposition_type="inline",
    )


@router.delete("/{entity}/{record_id}/{attachment_id}", name="system_delete_attachment")
async def delete_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Delete a specific attachment (file + DB record)."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    can_update = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    if not can_update and not _is_own_user_record(entity, record_id, user):
        return ActionResponse(status="error", message="Permission denied")

    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.entity_name == entity,
            Attachment.record_id == record_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        return ActionResponse(status="error", message="Attachment not found")

    await storage.delete(attachment.file_path)
    await db.delete(attachment)
    await db.commit()

    return ActionResponse(status="success", message="Attachment deleted")
