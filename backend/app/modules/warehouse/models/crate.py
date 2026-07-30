from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Crate(BaseModel):
    """Crate entity model."""
    __tablename__ = "crate"
    
    code: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, default=None)
    order: Mapped[str] = mapped_column(String(50), ForeignKey("order.id"), nullable=True, default=None)
    crate_class: Mapped[str] = mapped_column(String(50), ForeignKey("crate_class.id"), nullable=True, default=None)
    target: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    counted: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
