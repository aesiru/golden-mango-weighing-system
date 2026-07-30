from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Reading(BaseModel):
    """Reading entity model."""
    __tablename__ = "reading"
    
    crate: Mapped[str] = mapped_column(String(50), ForeignKey("crate.id"), nullable=True, default=None)
    order: Mapped[str] = mapped_column(String(50), ForeignKey("order.id"), nullable=True, default=None)
    weight_grams: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
