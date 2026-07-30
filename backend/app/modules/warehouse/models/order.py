from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Order(BaseModel):
    """Order entity model."""
    __tablename__ = "order"
    
    company: Mapped[str] = mapped_column(String(50), ForeignKey("company.id"), nullable=True, default=None)
    crate_class: Mapped[str] = mapped_column(String(50), ForeignKey("crate_class.id"), nullable=True, default=None)
    total_amount: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    current_amount: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    status: Mapped[str] = mapped_column(String(255), nullable=True, default="pending")
