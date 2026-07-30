"""
Auth Service
=============
Orchestrates authentication logic: login, token refresh, token validation.
Depends on AuthRepository and infrastructure auth services.
"""
from typing import Any, Optional
from dataclasses import dataclass, field

from app.domain.exceptions import PermissionDeniedError, EntityNotFoundError


@dataclass
class AuthenticatedUser:
    """Lightweight user representation returned by auth service."""
    id: str
    username: str
    roles: list[str]
    role_ids: list[str] = field(default_factory=list)
    is_superuser: bool = False


class AuthService:
    """Application-layer authentication orchestration."""

    def __init__(self, auth_repo, jwt_service, password_service):
        self.auth_repo = auth_repo
        self.jwt_service = jwt_service
        self.password_service = password_service

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user and return tokens."""
        user = await self.auth_repo.get_user_by_username(username)
        if not user:
            raise EntityNotFoundError("User", username)

        if not self.password_service.verify_password(password, user.hashed_password):
            raise PermissionDeniedError("Invalid credentials")

        if not user.is_active:
            raise PermissionDeniedError("Account is disabled")

        token_data = {
            "sub": user.username,
            "user_id": user.id,
        }
        access_token = self.jwt_service.create_access_token(token_data)
        refresh_token = self.jwt_service.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": AuthenticatedUser(
                id=user.id,
                username=user.username,
                roles=[r.name for r in user.roles],
                role_ids=[r.id for r in user.roles],
                is_superuser=user.is_superuser,
            ),
        }

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an access token using a refresh token."""
        payload = self.jwt_service.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise PermissionDeniedError("Invalid refresh token")

        username = payload.get("sub")
        if not username:
            raise PermissionDeniedError("Invalid refresh token")

        user = await self.auth_repo.get_user_by_username(username)
        if not user or not user.is_active:
            raise PermissionDeniedError("User not found or disabled")

        token_data = {"sub": user.username, "user_id": user.id}
        new_access_token = self.jwt_service.create_access_token(token_data)

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    async def validate_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Validate a token and return user info."""
        payload = self.jwt_service.decode_token(token)
        if not payload:
            return None

        username = payload.get("sub")
        if not username:
            return None

        user = await self.auth_repo.get_user_by_username(username)
        if not user:
            return None

        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            roles=[r.name for r in user.roles],
            role_ids=[r.id for r in user.roles],
            is_superuser=user.is_superuser,
        )
