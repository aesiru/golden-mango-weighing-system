"""
User Profile Routes
====================
Allows the logged-in user to view and update their own profile.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import User
from app.infrastructure.auth.password_service import PasswordService

router = APIRouter(tags=["profile"])


class ProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_number: Optional[str] = None
    department: Optional[str] = None
    site: Optional[str] = None
    employee_id: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    roles: list[str] = []


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class PasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)


@router.get("/profile")
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "error", "message": "User not found"}

    return {
        "status": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "contact_number": user.contact_number,
            "department": user.department,
            "site": user.site,
            "employee_id": user.employee_id,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "roles": [role.name for role in user.roles],
        },
    }


@router.put("/profile")
async def update_profile(
    data: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "error", "message": "User not found"}

    update_data = data.model_dump(exclude_unset=True)

    if "is_active" in update_data and not current_user.is_superuser:
        return {
            "status": "error",
            "message": "Only superusers can change account status",
        }

    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "Profile updated successfully",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "contact_number": user.contact_number,
            "department": user.department,
            "site": user.site,
            "employee_id": user.employee_id,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "roles": [role.name for role in user.roles],
        },
    }


@router.put("/profile/password")
async def update_password(
    data: PasswordUpdate,
    current_user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's password."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "error", "message": "User not found"}

    if data.new_password != data.confirm_password:
        return {
            "status": "error",
            "message": "New password and confirmation do not match",
        }

    if not PasswordService.verify_password(data.current_password, user.hashed_password):
        return {
            "status": "error",
            "message": "Current password is incorrect",
        }

    if PasswordService.verify_password(data.new_password, user.hashed_password):
        return {
            "status": "error",
            "message": "New password must be different from the current password",
        }

    user.hashed_password = PasswordService.hash_password(data.new_password)

    await db.commit()

    return {
        "status": "success",
        "message": "Password updated successfully",
    }
