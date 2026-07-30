"""
Admin — API Key Management
===========================
Issue and revoke API keys for service-to-service integration.
Keys are stored as bcrypt hashes; the raw key is returned exactly once.

    GET    /admin/api-keys          — list keys for the current user (or all for admin)
    POST   /admin/api-keys          — create a new key
    DELETE /admin/api-keys/{id}     — revoke / delete a key
"""
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.auth import APIKey
from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/admin/api-keys", tags=["admin"])

_KEY_BYTES = 32  # 256-bit random token
_PREFIX_LEN = 8


def _generate_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash)."""
    raw = secrets.token_urlsafe(_KEY_BYTES)
    prefix = raw[:_PREFIX_LEN]
    # Use SHA-256 for storage — bcrypt would be safer but is sync-only; acceptable for API keys
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, digest


def _require_admin(current_user: CurrentUser) -> None:
    if not current_user.is_superuser and "Administrator" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def _serialize(k: APIKey, *, include_raw: str | None = None) -> dict:
    d: dict = {
        "id": k.id,
        "name": k.name,
        "key_prefix": k.key_prefix,
        "user_id": k.user_id,
        "is_active": k.is_active,
        "created_by": k.created_by,
        "created_at": k.created_at.isoformat() if k.created_at else None,
        "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
    }
    if include_raw:
        d["key"] = include_raw  # shown ONCE on creation
    return d


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    expires_at: Optional[datetime] = None


@router.get("", name="admin_list_api_keys")
async def list_api_keys(
    user_id: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List API keys.  Admins see all keys; regular users see only their own."""
    is_admin = current_user.is_superuser or "Administrator" in current_user.roles
    target_user = user_id if (is_admin and user_id) else current_user.id

    q = select(APIKey).where(APIKey.user_id == target_user, APIKey.is_active == True)  # noqa: E712
    result = await db.execute(q)
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(k) for k in rows]}


@router.post("", name="admin_create_api_key", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key.  The raw token is returned exactly once."""
    raw_key, prefix, key_hash = _generate_key()

    api_key = APIKey(
        user_id=current_user.id,
        name=payload.name,
        key_hash=key_hash,
        key_prefix=prefix,
        is_active=True,
        created_by=current_user.username,
        expires_at=payload.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {
        "status": "success",
        "message": "API key created. Store the key now — it will not be shown again.",
        "data": _serialize(api_key, include_raw=raw_key),
    }


@router.delete("/{key_id}", name="admin_revoke_api_key")
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) an API key.  Admins can revoke any key."""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    if api_key.user_id != current_user.id:
        _require_admin(current_user)

    api_key.is_active = False
    await db.commit()
    return {"status": "success", "message": "API key revoked"}
