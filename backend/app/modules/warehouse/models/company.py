from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Company(BaseModel):
    """Company entity model."""
    __tablename__ = "company"
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    email: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, default=None)
    phone: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    address: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    registration_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(255), nullable=True, default="pending")
    user: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
