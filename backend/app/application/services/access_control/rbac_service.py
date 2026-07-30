"""
RBAC Application Service (CLEAN Architecture - Application Layer)
=================================================================
This is the PROPER CLEAN ARCHITECTURE implementation for RBAC.

ARCHITECTURE LAYERS:
-------------------
1. Domain Layer: Core business rules and entities (User, Role, EntityPermission)
2. Application Layer (THIS FILE): Orchestrates business logic, delegates to repositories
3. Infrastructure Layer: Database access, caching, external services
4. Interface Layer (API): FastAPI routes, HTTP handlers

CLEAN ARCHITECTURE PRINCIPLES:
------------------------------
- Dependency Inversion: Depends on abstractions (repository interfaces), not concrete implementations
- Dependency Injection: Receives dependencies via constructor, not creating them internally
- No Infrastructure Coupling: No imports of AsyncSession, cache, or DB models
- Single Responsibility: Only orchestrates business logic, delegates data access

MIGRATION STATUS:
-----------------
This is the TARGET implementation. The legacy file 'rbac.py' violates CLEAN architecture
by using static methods, direct DB access, and infrastructure coupling.

Migrate all API routes from:
    from app.application.services.access_control.rbac import RBACService
    RBACService.check_permission_async(db, user, entity, action)

To:
    from app.api.dependencies import get_rbac_service
    rbac: RBACAppService = Depends(get_rbac_service)
    await rbac.check_permission(user_id, entity, action, role_ids, is_superuser)

USAGE:
------
Constructor injection:
    rbac = RBACAppService(auth_repo)

Check permission:
    await rbac.check_permission(
        user_id=user.id,
        entity="work_order",
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )

Cache management:
    await rbac.load_cache(role_ids)  # Pre-load permissions
    rbac.clear_cache()  # Clear cache
"""
from typing import Any, Optional


class RBACAppService:
    """Application-layer RBAC that delegates to repository."""

    def __init__(self, auth_repo):
        self.auth_repo = auth_repo
        self._cache: dict[str, dict[str, bool]] = {}

    async def check_permission(
        self,
        user_id: str,
        entity: str,
        action: str,
        role_ids: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> bool:
        if is_superuser:
            return True

        if not role_ids:
            return False

        # Check cache first
        for role_id in role_ids:
            cache_key = f"{role_id}:{entity}"
            if cache_key in self._cache:
                perms = self._cache[cache_key]
                if perms.get(f"can_{action}"):
                    return True

        # Fall back to DB
        permissions = await self.auth_repo.get_entity_permissions(role_ids, entity)
        for perm in permissions:
            if action == "read" and perm.can_read:
                return True
            if action == "create" and perm.can_create:
                return True
            if action == "update" and perm.can_update:
                return True
            if action == "delete" and perm.can_delete:
                return True

        return False

    async def load_cache(self, role_ids: list[str]):
        """Pre-load permissions into cache for performance."""
        permissions = await self.auth_repo.get_entity_permissions(role_ids)
        for perm in permissions:
            for role_id in role_ids:
                cache_key = f"{role_id}:{perm.entity_name}"
                self._cache[cache_key] = {
                    "can_read": perm.can_read,
                    "can_create": perm.can_create,
                    "can_update": perm.can_update,
                    "can_delete": perm.can_delete,
                }

    def clear_cache(self):
        self._cache.clear()
