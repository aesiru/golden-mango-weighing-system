"""
Roles Router
============
Role management endpoints.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import ValidationError

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import User, Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.schemas.base import ActionResponse
from .common import api_response

router = APIRouter(tags=["admin-roles"])


@router.get("/meta/role")
async def get_role_metadata(current_user: CurrentUser = Depends(get_current_user_from_token)):
    """Get metadata for Role entity."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    
    return api_response(
        status="success",
        message="Role metadata retrieved",
        data={
            "entity": "role",
            "label": "Role",
            "title_field": "name",
            "fields": [
                {
                    "name": "name",
                    "label": "Name",
                    "field_type": "string",
                    "required": True,
                    "readonly": False,
                    "max_length": 100,
                },
                {
                    "name": "description",
                    "label": "Description",
                    "field_type": "text",
                    "required": False,
                    "readonly": False,
                    "max_length": 500,
                },
                {
                    "name": "is_active",
                    "label": "Active",
                    "field_type": "boolean",
                    "required": False,
                    "readonly": False,
                    "default": True,
                },
            ],
        },
    )


@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """List all roles with their permissions."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    
    return api_response(
        status="success",
        message="Roles retrieved successfully",
        data=[
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_active": r.is_active,
                "permissions": [
                    {
                        "id": p.id,
                        "entity_name": p.entity_name,
                        "can_read": p.can_read,
                        "can_create": p.can_create,
                        "can_update": p.can_update,
                        "can_delete": p.can_delete,
                        "in_sidebar": p.in_sidebar,
                    }
                    for p in r.permissions
                ],
            }
            for r in roles
        ]
    )


@router.post("/roles")
async def create_role(
    role_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Create a new role."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    try:
        validated_data = RoleCreate(**role_data)
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
        select(Role).where(Role.name == validated_data.name)
    )
    if existing.scalar_one_or_none():
        return api_response(
            status="error",
            message="Role name already exists",
            data={"errors": {"name": "Role name already exists"}}
        )
    
    role = Role(
        name=validated_data.name,
        description=validated_data.description or "",
        is_active=validated_data.is_active,
    )
    
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return api_response(
        status="success",
        message="Role created successfully",
        data={
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
        }
    )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    role_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update a role."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return api_response(status="error", message="Role not found")
    
    if role.name == "SystemManager":
        return api_response(
            status="error",
            message="Cannot modify SystemManager role"
        )
    
    try:
        validated_data = RoleUpdate(**role_data)
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
    
    if validated_data.name is not None:
        existing = await db.execute(
            select(Role).where(Role.name == validated_data.name).where(Role.id != role_id)
        )
        if existing.scalar_one_or_none():
            return api_response(
                status="error",
                message="Role name already exists",
                data={"errors": {"name": "Role name already exists"}}
            )
        role.name = validated_data.name
    if validated_data.description is not None:
        role.description = validated_data.description
    if validated_data.is_active is not None:
        role.is_active = validated_data.is_active
    
    await db.commit()
    
    return api_response(
        status="success",
        message="Role updated successfully",
        data={
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
        }
    )


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Delete a role."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied: Superuser required")
    
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        return api_response(status="error", message="Role not found")
    
    if role.name == "SystemManager":
        return api_response(
            status="error",
            message="Cannot delete SystemManager role"
        )
    
    users_with_role = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.roles.any(Role.id == role_id))
    )
    if users_with_role.scalar_one_or_none():
        return api_response(
            status="error",
            message="Cannot delete role that is assigned to users"
        )
    
    await db.delete(role)
    await db.commit()
    
    return api_response(
        status="success",
        message="Role deleted successfully"
    )
