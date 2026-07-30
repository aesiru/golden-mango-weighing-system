"""
Users Router
============
User management endpoints.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import ValidationError

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser, get_password_hash
from app.core.framework.models.auth import User, Role
from app.schemas.user import UserCreate, UserUpdate
from .common import api_response

router = APIRouter(tags=["admin-users"])


@router.get("/meta/user")
async def get_user_metadata(current_user: CurrentUser = Depends(get_current_user_from_token)):
    """Get metadata for User entity."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    return api_response(
        status="success",
        message="User metadata retrieved",
        data={
            "entity": "user",
            "label": "User",
            "title_field": "full_name",
            "fields": [
                {
                    "name": "username",
                    "label": "Username",
                    "field_type": "string",
                    "required": True,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "email",
                    "label": "Email",
                    "field_type": "email",
                    "required": True,
                    "readonly": False,
                    "max_length": 255,
                },
                {
                    "name": "full_name",
                    "label": "Full Name",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 255,
                },
                {
                    "name": "first_name",
                    "label": "First Name",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "last_name",
                    "label": "Last Name",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "contact_number",
                    "label": "Contact Number",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 50,
                },
                {
                    "name": "department",
                    "label": "Department",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "site",
                    "label": "Site",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "employee_id",
                    "label": "Employee ID",
                    "field_type": "string",
                    "required": False,
                    "readonly": False,
                    "max_length": 36,
                },
                {
                    "name": "password",
                    "label": "Password",
                    "field_type": "password",
                    "required": True,
                    "readonly": False,
                },
                {
                    "name": "is_active",
                    "label": "Active",
                    "field_type": "boolean",
                    "required": False,
                    "readonly": False,
                    "default": True,
                },
                {
                    "name": "is_superuser",
                    "label": "Superuser",
                    "field_type": "boolean",
                    "required": False,
                    "readonly": False,
                    "default": False,
                },
                {
                    "name": "role_ids",
                    "label": "Roles",
                    "field_type": "multi_select",
                    "required": False,
                    "readonly": False,
                    "link_entity": "role",
                },
            ],
        },
    )


@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """List all users with their roles and pagination."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    query = select(User).options(selectinload(User.roles))
    
    if search:
        query = query.where(
            User.username.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return api_response(
        status="success",
        message="Users retrieved successfully",
        data={
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "full_name": u.full_name,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "contact_number": u.contact_number,
                    "department": u.department,
                    "site": u.site,
                    "employee_id": u.employee_id,
                    "is_active": u.is_active,
                    "is_superuser": u.is_superuser,
                    "roles": [{"id": r.id, "name": r.name} for r in u.roles],
                }
                for u in users
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )


@router.post("/users")
async def create_user(
    user_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Create a new user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    try:
        validated_data = UserCreate(**user_data)
    except ValidationError as e:
        errors = {}
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            errors[field] = error['msg']
        return api_response(
            status="error",
            message="Validation failed",
            data={"errors": errors}
        )
    
    existing = await db.execute(
        select(User).where(
            (User.username == validated_data.username) |
            (User.email == validated_data.email)
        )
    )
    if existing.scalar_one_or_none():
        return api_response(
            status="error",
            message="Username or email already exists",
            data={"errors": {"_form": "Username or email already exists"}}
        )
    
    hashed_password = get_password_hash(validated_data.password)
    
    user = User(
        username=validated_data.username,
        email=validated_data.email,
        full_name=validated_data.full_name,
        first_name=validated_data.first_name,
        last_name=validated_data.last_name,
        contact_number=validated_data.contact_number,
        department=validated_data.department,
        site=validated_data.site,
        employee_id=validated_data.employee_id,
        hashed_password=hashed_password,
        is_active=validated_data.is_active,
        is_superuser=validated_data.is_superuser,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    if validated_data.role_ids:
        roles_result = await db.execute(select(Role).where(Role.id.in_(validated_data.role_ids)))
        user.roles = list(roles_result.scalars().all())
        await db.commit()
    
    return api_response(
        status="success",
        message="User created successfully",
        data={
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
        }
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return api_response(status="error", message="User not found")
    
    try:
        validated_data = UserUpdate(**user_data)
    except ValidationError as e:
        errors = {}
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            errors[field] = error['msg']
        return api_response(
            status="error",
            message="Validation failed",
            data={"errors": errors}
        )
    
    if validated_data.email and validated_data.email != user.email:
        existing = await db.execute(
            select(User).where(
                (User.email == validated_data.email) &
                (User.id != user_id)
            )
        )
        if existing.scalar_one_or_none():
            return api_response(
                status="error",
                message="Email already exists",
                data={"errors": {"email": "Email already exists"}}
            )
    
    if validated_data.username is not None:
        user.username = validated_data.username
    if validated_data.email is not None:
        user.email = validated_data.email
    if validated_data.full_name is not None:
        user.full_name = validated_data.full_name
    if validated_data.first_name is not None:
        user.first_name = validated_data.first_name
    if validated_data.last_name is not None:
        user.last_name = validated_data.last_name
    if validated_data.contact_number is not None:
        user.contact_number = validated_data.contact_number
    if validated_data.department is not None:
        user.department = validated_data.department
    if validated_data.site is not None:
        user.site = validated_data.site
    if validated_data.employee_id is not None:
        user.employee_id = validated_data.employee_id
    if validated_data.is_active is not None:
        user.is_active = validated_data.is_active
    if validated_data.is_superuser is not None:
        user.is_superuser = validated_data.is_superuser
    
    if validated_data.password:
        user.hashed_password = get_password_hash(validated_data.password)
    
    if validated_data.role_ids is not None:
        roles_result = await db.execute(select(Role).where(Role.id.in_(validated_data.role_ids)))
        user.roles = list(roles_result.scalars().all())
    
    await db.commit()
    
    return api_response(
        status="success",
        message="User updated successfully",
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Delete a user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return api_response(status="error", message="User not found")
    
    if user.id == current_user.id:
        return api_response(
            status="error",
            message="Cannot delete your own account"
        )
    
    await db.delete(user)
    await db.commit()
    
    return api_response(
        status="success",
        message="User deleted successfully"
    )


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: str,
    role_data: dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Assign a role to a user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"status": "error", "message": "User not found"}
    
    result = await db.execute(
        select(Role).where(Role.id == role_data["role_id"])
    )
    role = result.scalar_one_or_none()
    
    if not role:
        return {"status": "error", "message": "Role not found"}
    
    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
    
    return {"status": "success", "message": "Role assigned successfully"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Remove a role from a user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.roles)))
    user = result.scalar_one_or_none()
    if not user:
        return api_response(status="error", message="User not found")
    
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalar_one_or_none()
    if not role:
        return api_response(status="error", message="Role not found")
    
    if role not in user.roles:
        return api_response(status="error", message="User does not have this role")
    
    user.roles.remove(role)
    await db.commit()
    
    return api_response(status="success", message="Role removed successfully")


@router.post("/users/{user_id}/roles/{role_id}")
async def add_role_to_user(
    user_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Assign a role to a user."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.roles)))
    user = result.scalar_one_or_none()
    if not user:
        return api_response(status="error", message="User not found")
    
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalar_one_or_none()
    if not role:
        return api_response(status="error", message="Role not found")
    
    if role in user.roles:
        return api_response(status="error", message="User already has this role")
    
    user.roles.append(role)
    await db.commit()
    
    return api_response(status="success", message="Role assigned successfully")
