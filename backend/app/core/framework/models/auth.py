"""
Core Framework Authentication Models
==================================
User, Role, and EntityPermission models for the Core Framework.
These are system entities that require DEVELOPER_MODE to edit.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# Association table for User-Role many-to-many relationship
user_roles = Table(
    "core_user_roles",  # Renamed with core_ prefix
    Base.metadata,
    Column("user_id", String(36), ForeignKey("core_users.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("core_roles.id"), primary_key=True),
)


class User(Base):
    """Core Framework User model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    contact_number: Mapped[str] = mapped_column(String(50), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    site: Mapped[str] = mapped_column(String(100), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
    )


class Role(Base):
    """Core Framework Role model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_roles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)  # TEMP: required disabled
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )
    permissions: Mapped[list["EntityPermission"]] = relationship(
        "EntityPermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class EntityPermission(Base):
    """Core Framework EntityPermission model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_entity_permissions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_roles.id"), nullable=True)  # TEMP: required disabled
    entity_name: Mapped[str] = mapped_column(String(100), nullable=True)  # TEMP: required disabled
    can_read: Mapped[bool] = mapped_column(Boolean, default=False)
    can_create: Mapped[bool] = mapped_column(Boolean, default=False)
    can_update: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)
    can_select: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    can_export: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    can_import: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    in_sidebar: Mapped[bool] = mapped_column(Boolean, default=False)

    role: Mapped["Role"] = relationship("Role", back_populates="permissions")


class UserSession(Base):
    """Active user session — created on login, revoked on logout or by admin."""
    __tablename__ = "core_user_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class APIKey(Base):
    """Integration API key — issued by admin, used in Bearer auth as an alternative to JWT."""
    __tablename__ = "core_api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Store only a secure hash; the raw key is shown once on creation
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


__all__ = ["User", "Role", "EntityPermission", "user_roles", "UserSession", "APIKey"]
