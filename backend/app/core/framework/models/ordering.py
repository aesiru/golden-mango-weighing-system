"""Core Framework Ordering Models
=================================
ModuleOrder and EntityOrder models for the Core Framework.
These are system entities that require DEVELOPER_MODE to edit.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ModuleOrder(Base):
    """Core Framework ModuleOrder model - Stores display order of modules."""
    __tablename__ = "core_module_orders"
    __table_args__ = (
        UniqueConstraint("module_name", name="uq_core_module_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityOrder(Base):
    """Core Framework EntityOrder model - Stores display order of entities within modules."""
    __tablename__ = "core_entity_orders"
    __table_args__ = (
        UniqueConstraint("entity_name", name="uq_core_entity_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["ModuleOrder", "EntityOrder"]
