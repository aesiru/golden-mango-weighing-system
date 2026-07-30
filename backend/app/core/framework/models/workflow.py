"""Core Framework Workflow Models
=================================
WorkflowState, WorkflowAction, Workflow, WorkflowStateLink, and 
WorkflowTransition models for the Core Framework.
These are system entities that require DEVELOPER_MODE to edit.
"""
import uuid
import json
import re
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Boolean, Integer, DateTime, ForeignKey, Index, 
    UniqueConstraint, Text, event
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    pass


def generate_slug(label: str) -> str:
    """Convert label to slug: lowercase, replace spaces with underscores, remove special chars."""
    slug = label.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


class WorkflowState(Base):
    """Core Framework WorkflowState model - Global workflow state entity."""
    __tablename__ = "core_workflow_states"

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="neutral")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow_links: Mapped[List["WorkflowStateLink"]] = relationship(
        "WorkflowStateLink",
        back_populates="state",
        cascade="all, delete-orphan",
    )


class WorkflowAction(Base):
    """Core Framework WorkflowAction model - Global workflow action entity."""
    __tablename__ = "core_workflow_actions"

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="action_ref",
        cascade="all, delete-orphan",
    )


class Workflow(Base):
    """Core Framework Workflow model - Workflow configuration for a specific entity."""
    __tablename__ = "core_workflows"

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    target_entity: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    state_links: Mapped[List["WorkflowStateLink"]] = relationship(
        "WorkflowStateLink",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )


class WorkflowStateLink(Base):
    """Core Framework WorkflowStateLink model - Junction table linking state to workflow."""
    __tablename__ = "core_workflow_state_links"
    __table_args__ = (
        UniqueConstraint("workflow_id", "state_id", name="uq_core_workflow_state"),
        Index("ix_core_workflow_state_links_workflow", "workflow_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflows.id", ondelete="CASCADE"), 
        nullable=True
    )
    state_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflow_states.id", ondelete="RESTRICT"), 
        nullable=True
    )
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="state_links")
    state: Mapped["WorkflowState"] = relationship("WorkflowState", back_populates="workflow_links")


class WorkflowTransition(Base):
    """Core Framework WorkflowTransition model - Transition between states."""
    __tablename__ = "core_workflow_transitions"
    __table_args__ = (Index("ix_core_workflow_transitions_workflow", "workflow_id"),)

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflows.id", ondelete="CASCADE"), 
        nullable=True
    )
    from_state_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflow_states.id", ondelete="RESTRICT"), 
        nullable=True
    )
    action_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflow_actions.id", ondelete="RESTRICT"), 
        nullable=True
    )
    to_state_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("core_workflow_states.id", ondelete="RESTRICT"), 
        nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    allowed_roles: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        default=None
    )  # JSON array of role names

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="transitions")
    from_state: Mapped["WorkflowState"] = relationship("WorkflowState", foreign_keys=[from_state_id])
    action_ref: Mapped["WorkflowAction"] = relationship("WorkflowAction", back_populates="transitions")
    to_state: Mapped["WorkflowState"] = relationship("WorkflowState", foreign_keys=[to_state_id])

    def get_allowed_roles(self) -> list[str]:
        """Parse allowed_roles JSON string into a list."""
        if not self.allowed_roles:
            return []
        try:
            return json.loads(self.allowed_roles)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_allowed_roles(self, roles: list[str] | None):
        """Set allowed_roles from a list."""
        if not roles:
            self.allowed_roles = None
        else:
            self.allowed_roles = json.dumps(roles)


@event.listens_for(WorkflowState, "before_insert")
@event.listens_for(WorkflowState, "before_update")
def generate_state_slug(mapper, connection, target):
    if target.label:
        target.slug = generate_slug(target.label)


@event.listens_for(WorkflowAction, "before_insert")
@event.listens_for(WorkflowAction, "before_update")
def generate_action_slug(mapper, connection, target):
    if target.label:
        target.slug = generate_slug(target.label)


__all__ = [
    "generate_slug",
    "WorkflowState",
    "WorkflowAction",
    "Workflow",
    "WorkflowStateLink",
    "WorkflowTransition",
]
