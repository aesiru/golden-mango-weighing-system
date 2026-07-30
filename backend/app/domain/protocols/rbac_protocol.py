"""
RBAC Protocol
==============
Abstract interface for role-based access control.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class RBACProtocol(Protocol):
    """Interface for permission checks."""

    async def check_permission(
        self,
        user_id: str,
        entity: str,
        action: str,
        role_ids: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> bool:
        """Check if a user has permission to perform an action on an entity."""
        ...

    async def get_entity_permissions(
        self,
        role_ids: list[str],
        entity: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get permissions for given roles, optionally filtered by entity."""
        ...
