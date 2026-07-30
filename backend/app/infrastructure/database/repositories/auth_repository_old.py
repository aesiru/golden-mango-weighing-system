"""
Auth Repository
================
Concrete SQLAlchemy implementation for user/role data access.
Extracted from rbac.py to follow Clean Architecture - no business logic, only data operations.
"""
from typing import Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.framework.models.auth import User, Role, EntityPermission


class AuthRepository:
    """Concrete auth repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with roles loaded."""
        result = await self.db.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get role names for a user."""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        if not user:
            return []
        return [role.name for role in user.roles]

    # =========================================================================
    # PERMISSION OPERATIONS
    # =========================================================================

    async def get_permission_for_role_and_entity(
        self, role_id: str, entity_name: str
    ) -> Optional[EntityPermission]:
        """Get a specific permission for a role and entity."""
        result = await self.db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id == role_id)
            .where(EntityPermission.entity_name == entity_name)
        )
        return result.scalar_one_or_none()
    
    async def get_all_permissions_for_role(self, role_id: str) -> List[EntityPermission]:
        """Get all entity permissions for a role."""
        result = await self.db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id == role_id)
        )
        return list(result.scalars().all())
    
    async def get_permissions_for_user_roles(self, role_ids: List[str]) -> List[EntityPermission]:
        """Get all permissions for multiple roles."""
        result = await self.db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id.in_(role_ids))
        )
        return list(result.scalars().all())

    # =========================================================================
    # ROLE OPERATIONS
    # =========================================================================

    async def get_role_by_name(self, role_name: str) -> Optional[Role]:
        """Get role by name with permissions loaded."""
        result = await self.db.execute(
            select(Role)
            .where(Role.name == role_name)
            .options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()
    
    async def get_all_roles(self) -> List[Role]:
        """Get all roles with permissions."""
        result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
        )
        return list(result.scalars().all())
        """Get user by username from core_users table only."""
        result = await self.db.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def get_user_roles(self, user_id: str) -> list[str]:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        if not user:
            return []
        return [role.name for role in user.roles]

    async def get_entity_permissions(
        self,
        role_ids: list[str],
        entity: Optional[str] = None,
    ) -> list[EntityPermission]:
        query = select(EntityPermission).where(EntityPermission.role_id.in_(role_ids))
        if entity:
            query = query.where(EntityPermission.entity_name == entity)
        result = await self.db.execute(query)
        return list(result.scalars().all())
