"""
Core Framework Infrastructure Schemas
======================================
Pydantic schemas for ErrorLog, AuditLog, and Attachment entities.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ErrorLog Schemas
class ErrorLogBase(BaseModel):
    """Base ErrorLog schema with common fields."""
    status: Optional[int] = None
    title: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = None


class ErrorLogCreate(ErrorLogBase):
    """Schema for creating a new ErrorLog."""
    pass


class ErrorLogInDB(ErrorLogBase):
    """Schema for ErrorLog as stored in database."""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ErrorLog(ErrorLogInDB):
    """Public ErrorLog schema."""
    pass


# AuditLog Schemas
class AuditLogBase(BaseModel):
    """Base AuditLog schema with common fields."""
    entity_name: str = Field(..., max_length=100)
    record_id: str = Field(..., max_length=50)
    action: str = Field(..., max_length=20)  # create, update, delete, workflow
    user_id: Optional[str] = Field(None, max_length=50)
    username: Optional[str] = Field(None, max_length=100)
    before_snapshot: Optional[str] = None
    after_snapshot: Optional[str] = None
    changed_fields: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    """Schema for creating a new AuditLog."""
    pass


class AuditLogInDB(AuditLogBase):
    """Schema for AuditLog as stored in database."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLog(AuditLogInDB):
    """Public AuditLog schema."""
    pass


# Attachment Schemas
class AttachmentBase(BaseModel):
    """Base Attachment schema with common fields."""
    entity_name: str = Field(..., max_length=100)
    record_id: str = Field(..., max_length=100)
    file_name: str = Field(..., max_length=255)
    original_name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    file_size: int = Field(default=0, ge=0)
    mime_type: Optional[str] = Field(None, max_length=100)
    uploaded_by: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class AttachmentCreate(AttachmentBase):
    """Schema for creating a new Attachment."""
    pass


class AttachmentUpdate(BaseModel):
    """Schema for updating an existing Attachment."""
    description: Optional[str] = None


class AttachmentInDB(AttachmentBase):
    """Schema for Attachment as stored in database."""
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Attachment(AttachmentInDB):
    """Public Attachment schema."""
    pass


# Export all schemas
__all__ = [
    "ErrorLogBase", "ErrorLogCreate", "ErrorLogInDB", "ErrorLog",
    "AuditLogBase", "AuditLogCreate", "AuditLogInDB", "AuditLog",
    "AttachmentBase", "AttachmentCreate", "AttachmentUpdate", "AttachmentInDB", "Attachment"
]
