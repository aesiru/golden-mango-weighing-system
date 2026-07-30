# Re-export shim — canonical definitions live in app.api.schemas.user
from app.api.schemas.user import UserCreate, UserUpdate  # noqa: F401

__all__ = ["UserCreate", "UserUpdate"]
