"""
Core Framework Infrastructure Models
====================================
ErrorLog, AuditLog, Attachment, EmailLog, NotificationSubscription, 
and ScheduledJobLog models for the Core Framework.
These are system entities that require DEVELOPER_MODE to edit.
"""
import uuid
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, func,
    Boolean, UniqueConstraint, Float
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ErrorLog(Base):
    """Core Framework ErrorLog model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_error_log"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    status: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    title: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    message: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Core Framework AuditLog model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_audit_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create, update, delete, workflow
    user_id: Mapped[str] = mapped_column(String(50), nullable=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    before_snapshot: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    after_snapshot: Mapped[str] = mapped_column(Text, nullable=True)   # JSON string
    changed_fields: Mapped[str] = mapped_column(Text, nullable=True)   # JSON list of field names
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Attachment(Base):
    """Core Framework Attachment model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_attachment"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EmailLog(Base):
    """Core Framework EmailLog model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_email_log"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    cc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    bcc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    from_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    record_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    event_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    html_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    recipient_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    sent_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class NotificationSubscription(Base):
    """Core Framework NotificationSubscription model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_notification_subscription"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "event", name="uq_core_notification_subscription_user_entity_event"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("core_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None, index=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledJobLog(Base):
    """Core Framework ScheduledJobLog model - System entity requiring DEVELOPER_MODE to edit."""
    __tablename__ = "core_scheduled_job_log"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    job_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    records_created: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    trigger_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


__all__ = [
    "ErrorLog",
    "AuditLog",
    "Attachment",
    "EmailLog",
    "NotificationSubscription",
    "ScheduledJobLog",
    "Comment",
    "Favorite",
    "Tag",
    "RecordTag",
    "UserActivity",
    "Series",
]


class Comment(Base):
    """Threaded comment on any entity record."""
    __tablename__ = "core_comment"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("core_comment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    author_username: Mapped[str] = mapped_column(String(100), nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Favorite(Base):
    """User-pinned record."""
    __tablename__ = "core_favorite"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_name", "record_id", name="uq_core_favorite_user_entity_record"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Tag(Base):
    """User-defined label (scoped to a user or system-wide)."""
    __tablename__ = "core_tag"
    __table_args__ = (
        UniqueConstraint("name", "created_by", name="uq_core_tag_name_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RecordTag(Base):
    """Association between a tag and a specific entity record."""
    __tablename__ = "core_record_tag"
    __table_args__ = (
        UniqueConstraint("tag_id", "entity_name", "record_id", name="uq_core_record_tag"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_tag.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tagged_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DiagramLayout(Base):
    """Saved named views (filter presets) for the position diagram."""
    __tablename__ = "core_diagram_layout"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    filters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {location, system}
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UserActivity(Base):
    """Tracks user page visits and activities for personalized home page recommendations."""
    __tablename__ = "core_user_activity"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_type", "entity_name", "page_path", name="uq_core_user_activity_unique"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # entity_view, page_visit, quick_create, admin_action
    entity_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    page_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    page_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # Weighted score for ranking
    last_visited_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Series(Base):
    """Tracks naming series for generating human-readable IDs (e.g., AST-0001, WO-0001)."""
    __tablename__ = "core_series"

    name: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
