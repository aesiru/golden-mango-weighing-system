"""
Core Framework Schemas - Public API
"""
from .auth import (
    UserBase, UserCreate, UserUpdate, UserInDB, User, UserWithRoles,
    RoleBase, RoleCreate, RoleUpdate, RoleInDB, Role,
    EntityPermissionBase, EntityPermissionCreate, EntityPermissionUpdate,
    EntityPermissionInDB, EntityPermission
)
from .infrastructure import (
    ErrorLogBase, ErrorLogCreate, ErrorLogInDB, ErrorLog,
    AuditLogBase, AuditLogCreate, AuditLogInDB, AuditLog,
    AttachmentBase, AttachmentCreate, AttachmentUpdate, AttachmentInDB, Attachment
)

__all__ = [
    # Auth schemas
    "UserBase", "UserCreate", "UserUpdate", "UserInDB", "User", "UserWithRoles",
    "RoleBase", "RoleCreate", "RoleUpdate", "RoleInDB", "Role",
    "EntityPermissionBase", "EntityPermissionCreate", "EntityPermissionUpdate",
    "EntityPermissionInDB", "EntityPermission",
    # Infrastructure schemas
    "ErrorLogBase", "ErrorLogCreate", "ErrorLogInDB", "ErrorLog",
    "AuditLogBase", "AuditLogCreate", "AuditLogInDB", "AuditLog",
    "AttachmentBase", "AttachmentCreate", "AttachmentUpdate", "AttachmentInDB", "Attachment"
]
