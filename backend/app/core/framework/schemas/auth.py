"""
Core Framework Authentication Schemas
=====================================
Pydantic schemas for User, Role, and EntityPermission entities.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """Base User schema with common fields."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    contact_number: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    site: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=36)


class UserCreate(UserBase):
    """Schema for creating a new User."""
    password: str = Field(..., min_length=8, max_length=255)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """Schema for updating an existing User."""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    contact_number: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    site: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=36)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserInDB(UserBase):
    """Schema for User as stored in database."""
    id: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class User(UserInDB):
    """Public User schema."""
    roles: List["Role"] = []


class UserWithRoles(User):
    """User schema with populated roles."""
    roles: List["Role"] = []


class RoleBase(BaseModel):
    """Base Role schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class RoleCreate(RoleBase):
    """Schema for creating a new Role."""
    pass


class RoleUpdate(BaseModel):
    """Schema for updating an existing Role."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class RoleInDB(RoleBase):
    """Schema for Role as stored in database."""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Role(RoleInDB):
    """Public Role schema."""
    users: List[User] = []
    permissions: List["EntityPermission"] = []  # Forward reference as string


class EntityPermissionBase(BaseModel):
    """Base EntityPermission schema with common fields."""
    entity_name: str = Field(..., min_length=1, max_length=100)
    can_read: bool = False
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_select: bool = False
    can_export: bool = False
    can_import: bool = False
    in_sidebar: bool = False


class EntityPermissionCreate(EntityPermissionBase):
    """Schema for creating a new EntityPermission."""
    role_id: str


class EntityPermissionUpdate(BaseModel):
    """Schema for updating an existing EntityPermission."""
    entity_name: Optional[str] = Field(None, min_length=1, max_length=100)
    can_read: Optional[bool] = None
    can_create: Optional[bool] = None
    can_update: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_select: Optional[bool] = None
    can_export: Optional[bool] = None
    can_import: Optional[bool] = None
    in_sidebar: Optional[bool] = None


class EntityPermissionInDB(EntityPermissionBase):
    """Schema for EntityPermission as stored in database."""
    id: str
    role_id: str
    
    class Config:
        from_attributes = True


class EntityPermission(EntityPermissionInDB):
    """Public EntityPermission schema."""
    role: Optional["Role"] = None  # Forward reference as string


# Forward references for circular relationships
User.model_rebuild()
Role.model_rebuild()

# Export all schemas
__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserInDB", "User", "UserWithRoles",
    "RoleBase", "RoleCreate", "RoleUpdate", "RoleInDB", "Role",
    "EntityPermissionBase", "EntityPermissionCreate", "EntityPermissionUpdate", 
    "EntityPermissionInDB", "EntityPermission"
]
