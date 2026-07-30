"""
Data Transfer Objects
======================
Lightweight data containers for passing between layers.
"""
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class PaginatedResult:
    """Result of a paginated query."""
    data: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


@dataclass
class ActionResult:
    """Result of a CRUD or workflow action."""
    status: str  # "success" or "error"
    message: str
    data: Optional[Any] = None
    errors: Optional[dict[str, str]] = None
