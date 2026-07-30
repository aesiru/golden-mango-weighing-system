from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class CrateClass(BaseModel):
    """crate_class entity model."""
    __tablename__ = "crate_class"

    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    min_weight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True, default=None)
    max_weight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True, default=None)