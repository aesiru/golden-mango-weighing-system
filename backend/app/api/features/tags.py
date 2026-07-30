"""
Tags Feature
============
User-defined labels that can be applied to any entity record.

    GET    /tags                              — list all tags owned by current user
    POST   /tags                              — create a new tag
    DELETE /tags/{id}                         — delete a tag (removes all associations)
    POST   /tags/{id}/apply/{entity}/{rid}    — apply tag to a record
    DELETE /tags/{id}/apply/{entity}/{rid}    — remove tag from a record
    GET    /tags/on/{entity}/{rid}            — get all tags on a specific record
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.infrastructure import Tag, RecordTag
from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20, description="Hex color, e.g. #3b82f6")


def _serialize_tag(t: Tag) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "color": t.color,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_record_tag(rt: RecordTag, tag: Optional[Tag] = None) -> dict:
    d: dict = {
        "id": rt.id,
        "tag_id": rt.tag_id,
        "entity_name": rt.entity_name,
        "record_id": rt.record_id,
        "tagged_by": rt.tagged_by,
        "created_at": rt.created_at.isoformat() if rt.created_at else None,
    }
    if tag:
        d["tag"] = _serialize_tag(tag)
    return d


@router.get("", name="list_tags")
async def list_tags(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List tags created by the current user."""
    result = await db.execute(
        select(Tag).where(Tag.created_by == current_user.username).order_by(Tag.name)
    )
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize_tag(t) for t in rows]}


@router.post("", name="create_tag", status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    # Check uniqueness for this user
    existing = await db.execute(
        select(Tag).where(Tag.name == payload.name, Tag.created_by == current_user.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Tag '{payload.name}' already exists")

    tag = Tag(name=payload.name, color=payload.color, created_by=current_user.username)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"status": "success", "data": _serialize_tag(tag)}


@router.delete("/{tag_id}", name="delete_tag")
async def delete_tag(
    tag_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tag and all its record associations."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.created_by != current_user.username and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.delete(tag)
    await db.commit()
    return {"status": "success", "message": "Tag deleted"}


@router.post("/{tag_id}/apply/{entity}/{record_id}", name="apply_tag")
async def apply_tag(
    tag_id: str,
    entity: str,
    record_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a tag to an entity record."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Idempotent
    existing = await db.execute(
        select(RecordTag).where(
            RecordTag.tag_id == tag_id,
            RecordTag.entity_name == entity,
            RecordTag.record_id == record_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "success", "message": "Already applied"}

    rt = RecordTag(
        tag_id=tag_id,
        entity_name=entity,
        record_id=record_id,
        tagged_by=current_user.username,
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return {"status": "success", "data": _serialize_record_tag(rt, tag)}


@router.delete("/{tag_id}/apply/{entity}/{record_id}", name="remove_tag")
async def remove_tag(
    tag_id: str,
    entity: str,
    record_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a tag from an entity record."""
    result = await db.execute(
        select(RecordTag).where(
            RecordTag.tag_id == tag_id,
            RecordTag.entity_name == entity,
            RecordTag.record_id == record_id,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=404, detail="Tag not applied to this record")

    await db.delete(rt)
    await db.commit()
    return {"status": "success", "message": "Tag removed"}


@router.get("/on/{entity}/{record_id}", name="get_record_tags")
async def get_record_tags(
    entity: str,
    record_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all tags currently applied to a specific record."""
    rts = await db.execute(
        select(RecordTag).where(RecordTag.entity_name == entity, RecordTag.record_id == record_id)
    )
    record_tags = rts.scalars().all()

    data = []
    for rt in record_tags:
        tag_res = await db.execute(select(Tag).where(Tag.id == rt.tag_id))
        tag = tag_res.scalar_one_or_none()
        data.append(_serialize_record_tag(rt, tag))

    return {"status": "success", "data": data}
