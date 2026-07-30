"""
Core Layer: Authentication & Security

JWT token handling, password hashing, current user extraction.

Clean Architecture Layer: Core
Responsibility: Provide authentication and security utilities
"""
from typing import Optional
from dataclasses import dataclass, field
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError
import bcrypt
from app.core.database import get_db


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@dataclass
class CurrentUser:
    id: str
    username: str
    roles: list[str]
    role_ids: list[str] = field(default_factory=list)
    employee_id: Optional[str] = None
    is_superuser: bool = False


async def get_current_user_from_token(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """Extract user from JWT token."""
    from app.core.config import settings
    from app.core.framework.models.auth import User
    
    # Default anonymous user with no permissions
    if not authorization or not authorization.startswith("Bearer "):
        return CurrentUser(
            id="anonymous",
            username="anonymous",
            roles=[],
            role_ids=[],
            is_superuser=False
        )
    
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        if db:
            result = await db.execute(
                select(User).where(User.username == username).options(selectinload(User.roles))
            )
            user = result.scalar_one_or_none()
            
            if user:
                return CurrentUser(
                    id=user.id,
                    username=user.username,
                    roles=[r.name for r in user.roles],
                    role_ids=[r.id for r in user.roles],
                    employee_id=user.employee_id,
                    is_superuser=user.is_superuser
                )
        
        # Fallback if no db session - use token data
        return CurrentUser(
            id=user_id or "unknown",
            username=username,
            roles=[],
            role_ids=[],
            employee_id=None,
            is_superuser=False
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def require_authenticated_user(
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> CurrentUser:
    if current_user.id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def get_current_user() -> CurrentUser:
    """Deprecated: Returns anonymous user. Use get_current_user_from_token instead."""
    return CurrentUser(
        id="anonymous",
        username="anonymous",
        roles=[],
        role_ids=[],
        employee_id=None,
        is_superuser=False
    )
