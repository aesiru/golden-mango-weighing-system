"""
Auth Repository Protocol
=========================
Abstract interface for authentication data access.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class AuthRepositoryProtocol(Protocol):
    """Interface for user/role data access."""

    async def get_user_by_username(self, username: str) -> Optional[Any]:
        """Fetch user by username, including roles."""
        ...

    async def get_user_by_id(self, user_id: str) -> Optional[Any]:
        """Fetch user by ID, including roles."""
        ...

    async def get_user_roles(self, user_id: str) -> list[Any]:
        """Get roles for a user."""
        ...

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        ...
