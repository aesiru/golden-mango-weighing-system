"""
Favorites Feature
=================
User-pinned records for quick access.

    GET    /favorites              — list current user's favorites
    POST   /favorites              — pin a record
    DELETE /favorites/{id}         — unpin a record
    GET    /favorites/{entity}     — favorites for a specific entity type
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.infrastructure import Favorite
from app.core.security import CurrentUser, require_authenticated_user
from app.meta.registry import MetaRegistry

router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteCreate(BaseModel):
    entity_name: str = Field(..., min_length=1)
    record_id: str = Field(..., min_length=1)
    label: Optional[str] = Field(None, max_length=200)


def _serialize(f: Favorite) -> dict:
    return {
        "id": f.id,
        "entity_name": f.entity_name,
        "record_id": f.record_id,
        "label": f.label,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("", name="list_favorites")
async def list_favorites(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List all pinned records for the current user."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(f) for f in rows], "total": len(rows)}


@router.get("/{entity}", name="list_favorites_by_entity")
async def list_favorites_by_entity(
    entity: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List favorites for the current user filtered to one entity type."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id, Favorite.entity_name == entity)
        .order_by(Favorite.created_at.desc())
    )
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(f) for f in rows]}


@router.post("", name="add_favorite", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    payload: FavoriteCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Pin a record."""
    if not MetaRegistry.get(payload.entity_name):
        raise HTTPException(status_code=404, detail=f"Entity '{payload.entity_name}' not found")

    # Idempotent — return existing if already pinned
    existing = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.entity_name == payload.entity_name,
            Favorite.record_id == payload.record_id,
        )
    )
    fav = existing.scalar_one_or_none()
    if fav:
        return {"status": "success", "data": _serialize(fav), "message": "Already pinned"}

    fav = Favorite(
        user_id=current_user.id,
        entity_name=payload.entity_name,
        record_id=payload.record_id,
        label=payload.label,
    )
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return {"status": "success", "data": _serialize(fav)}


@router.delete("/{favorite_id}", name="remove_favorite")
async def remove_favorite(
    favorite_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Unpin a record."""
    result = await db.execute(
        select(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == current_user.id)
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await db.delete(fav)
    await db.commit()
    return {"status": "success", "message": "Unpinned"}
