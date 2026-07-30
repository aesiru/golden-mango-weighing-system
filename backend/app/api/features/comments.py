"""
Comments Feature
================
Threaded comments on any entity record.

    GET    /comments/{entity}/{record_id}           — list comments for a record
    POST   /comments/{entity}/{record_id}           — add a comment
    PUT    /comments/{entity}/{record_id}/{id}      — edit own comment
    DELETE /comments/{entity}/{record_id}/{id}      — delete own comment (or admin)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.infrastructure import Comment
from app.core.security import CurrentUser, require_authenticated_user
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service
from app.meta.registry import MetaRegistry

router = APIRouter(prefix="/comments", tags=["comments"])


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)
    parent_id: Optional[str] = None


class CommentUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


def _serialize(c: Comment) -> dict:
    return {
        "id": c.id,
        "entity_name": c.entity_name,
        "record_id": c.record_id,
        "parent_id": c.parent_id,
        "body": c.body,
        "author_id": c.author_id,
        "author_username": c.author_username,
        "is_edited": c.is_edited,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/{entity}/{record_id}", name="list_comments")
async def list_comments(
    entity: str,
    record_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """List all comments for a record (flat + threaded)."""
    if not MetaRegistry.get(entity):
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")
    if not await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await db.execute(
        select(Comment)
        .where(Comment.entity_name == entity, Comment.record_id == record_id)
        .order_by(Comment.created_at.asc())
    )
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(c) for c in rows], "total": len(rows)}


@router.post("/{entity}/{record_id}", name="add_comment", status_code=status.HTTP_201_CREATED)
async def add_comment(
    entity: str,
    record_id: str,
    payload: CommentCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Add a comment to a record."""
    if not MetaRegistry.get(entity):
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")
    if not await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    comment = Comment(
        entity_name=entity,
        record_id=record_id,
        parent_id=payload.parent_id,
        body=payload.body,
        author_id=current_user.id,
        author_username=current_user.username,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"status": "success", "data": _serialize(comment)}


@router.put("/{entity}/{record_id}/{comment_id}", name="edit_comment")
async def edit_comment(
    entity: str,
    record_id: str,
    comment_id: str,
    payload: CommentUpdate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit an existing comment (own comment only)."""
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.entity_name == entity, Comment.record_id == record_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    comment.body = payload.body
    comment.is_edited = True
    await db.commit()
    await db.refresh(comment)
    return {"status": "success", "data": _serialize(comment)}


@router.delete("/{entity}/{record_id}/{comment_id}", name="delete_comment")
async def delete_comment(
    entity: str,
    record_id: str,
    comment_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment (own comment, or admin)."""
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.entity_name == entity, Comment.record_id == record_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_admin = current_user.is_superuser or "Administrator" in current_user.roles
    if comment.author_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.delete(comment)
    await db.commit()
    return {"status": "success", "message": "Comment deleted"}
