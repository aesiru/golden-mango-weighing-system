"""
Admin — Session Management
==========================
List and revoke active user sessions.  Superadmin-only.

    GET    /admin/sessions        — all active sessions (paginated)
    GET    /admin/sessions/me     — current user's own sessions
    DELETE /admin/sessions/{id}   — revoke a specific session
    DELETE /admin/sessions/user/{user_id} — revoke all sessions for a user
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.framework.models.auth import UserSession
from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/admin/sessions", tags=["admin"])


def _require_admin(current_user: CurrentUser) -> None:
    if not current_user.is_superuser and "Administrator" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def _serialize(s: UserSession) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "ip_address": s.ip_address,
        "user_agent": s.user_agent,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "is_revoked": s.is_revoked,
        "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
    }


@router.get("", name="admin_list_sessions")
async def list_sessions(
    user_id: Optional[str] = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List all sessions (admin)."""
    _require_admin(current_user)

    filters = []
    if user_id:
        filters.append(UserSession.user_id == user_id)
    if active_only:
        filters.append(UserSession.is_revoked == False)  # noqa: E712
        filters.append(UserSession.expires_at > datetime.utcnow())

    q = (
        select(UserSession)
        .where(and_(*filters) if filters else True)
        .order_by(UserSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(s) for s in rows], "page": page, "page_size": page_size}


@router.get("/me", name="admin_my_sessions")
async def my_sessions(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's own active sessions."""
    q = (
        select(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.is_revoked == False,  # noqa: E712
            UserSession.expires_at > datetime.utcnow(),
        )
        .order_by(UserSession.created_at.desc())
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return {"status": "success", "data": [_serialize(s) for s in rows]}


@router.delete("/{session_id}", name="admin_revoke_session")
async def revoke_session(
    session_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session (admin or session owner)."""
    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Allow owner to revoke their own session, otherwise require admin
    if session.user_id != current_user.id:
        _require_admin(current_user)

    session.is_revoked = True
    session.revoked_at = datetime.utcnow()
    await db.commit()
    return {"status": "success", "message": "Session revoked"}


@router.delete("/user/{user_id}", name="admin_revoke_user_sessions")
async def revoke_user_sessions(
    user_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active sessions for a user (admin-only)."""
    _require_admin(current_user)

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,  # noqa: E712
        )
    )
    sessions = result.scalars().all()
    now = datetime.utcnow()
    for s in sessions:
        s.is_revoked = True
        s.revoked_at = now

    await db.commit()
    return {"status": "success", "message": f"Revoked {len(sessions)} session(s)"}
