"""
Domain Layer: Branding Store Protocol

Defines the contract for branding data persistence.
Infrastructure implementations handle the actual storage mechanism.

Clean Architecture Layer: Domain
Responsibility: Define the interface for branding data storage
"""
from __future__ import annotations

from typing import Any, Protocol


class BrandingStoreProtocol(Protocol):
    """Protocol for branding data persistence operations."""
    
    def load(self) -> dict[str, Any]:
        """Load branding data from storage."""
        ...
    
    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        """Save branding data to storage."""
        ...
