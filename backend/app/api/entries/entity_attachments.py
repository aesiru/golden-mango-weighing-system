"""
Entity Attachment Routes — thin context resolver
=================================================
Resolves entity + record context, checks the metadata ``attachments`` flag,
then delegates all logic to api/system/attachments.py.

URL layout (served under /api/entity/):
    GET    /{entity}/{record_id}/attachments
    POST   /{entity}/{record_id}/attachments
    GET    /{entity}/{record_id}/attachments/{id}/download
    GET    /{entity}/{record_id}/attachments/{id}/view
    DELETE /{entity}/{record_id}/attachments/{id}
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.infrastructure.storage import get_storage, StorageBackend
from app.schemas.base import ActionResponse
from app.api.dependencies import get_rbac_service
from app.application.services.access_control.rbac_service import RBACAppService
# Import authoritative handlers from the system layer
from app.api.system.attachments import (
    list_attachments as _list,
    upload_attachment as _upload,
    download_attachment as _download,
    view_attachment as _view,
    delete_attachment as _delete,
)

router = APIRouter(tags=["attachments"])


# ---------------------------------------------------------------------------
# Thin delegators — entity/{entity}/{record_id}/attachments[/...]
# ---------------------------------------------------------------------------


@router.get("/{entity}/{record_id}/attachments", name="list_attachments")
async def list_attachments(
    entity: str,
    record_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """List attachments for a record.  Delegates to system/attachments."""
    return await _list(entity=entity, record_id=record_id, authorization=authorization, db=db, rbac=rbac)


@router.post("/{entity}/{record_id}/attachments", name="upload_attachment")
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
    """Upload a file attachment.  Delegates to system/attachments."""
    return await _upload(
        entity=entity,
        record_id=record_id,
        file=file,
        description=description,
        authorization=authorization,
        db=db,
        storage=storage,
        rbac=rbac,
    )


@router.get(
    "/{entity}/{record_id}/attachments/{attachment_id}/download",
    name="download_attachment",
)
async def download_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Download a file.  Delegates to system/attachments."""
    return await _download(
        entity=entity,
        record_id=record_id,
        attachment_id=attachment_id,
        authorization=authorization,
        token=token,
        db=db,
        rbac=rbac,
    )


@router.get(
    "/{entity}/{record_id}/attachments/{attachment_id}/view",
    name="view_attachment",
)
async def view_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """View a file inline.  Delegates to system/attachments."""
    return await _view(
        entity=entity,
        record_id=record_id,
        attachment_id=attachment_id,
        authorization=authorization,
        token=token,
        db=db,
        rbac=rbac,
    )


@router.delete(
    "/{entity}/{record_id}/attachments/{attachment_id}",
    name="delete_attachment",
)
async def delete_attachment(
    entity: str,
    record_id: str,
    attachment_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Delete an attachment.  Delegates to system/attachments."""
    return await _delete(
        entity=entity,
        record_id=record_id,
        attachment_id=attachment_id,
        authorization=authorization,
        db=db,
        storage=storage,
        rbac=rbac,
    )
