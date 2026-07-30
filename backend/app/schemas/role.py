# Re-export shim — canonical definitions live in app.api.schemas.role
from app.api.schemas.role import RoleCreate, RoleUpdate  # noqa: F401

__all__ = ["RoleCreate", "RoleUpdate"]
