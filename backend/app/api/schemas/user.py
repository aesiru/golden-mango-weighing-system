from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator
import re


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, description="Username is required")
    email: EmailStr = Field(..., description="Valid email is required")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name is required")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    contact_number: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    site: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=36)
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role_ids: Optional[List[str]] = []

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Username is required")
        trimmed_value = v.strip()
        if not re.match(r'^[a-zA-Z0-9_-]+$', trimmed_value):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return trimmed_value

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Full name is required")
        return v.strip()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=6)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    contact_number: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    site: Optional[str] = Field(None, max_length=100)
    employee_id: Optional[str] = Field(None, max_length=36)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[List[str]] = []

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed_value = v.strip()
            if trimmed_value == "":
                raise ValueError("Username cannot be empty")
            if not re.match(r'^[a-zA-Z0-9_-]+$', trimmed_value):
                raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
            return trimmed_value
        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if v.strip() == "":
                raise ValueError("Full name cannot be empty")
            return v.strip()
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "":
            if len(v) < 6:
                raise ValueError("Password must be at least 6 characters long")
        return v
