"""
Entity Repository Protocol
===========================
Abstract interface for generic entity CRUD operations.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class EntityRepositoryProtocol(Protocol):
    """Interface for entity data access."""

    def get_model(self, entity: str) -> Optional[Any]:
        """Get the ORM model class for an entity name."""
        ...

    async def get_by_id(self, entity: str, record_id: str) -> Optional[Any]:
        """Fetch a single record by entity name and ID."""
        ...

    async def get_list(
        self,
        entity: str,
        filters: Optional[dict] = None,
        search: Optional[str] = None,
        search_fields: Optional[list[str]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Fetch paginated list of records. Returns (records, total_count)."""
        ...

    async def create(self, entity: str, data: dict[str, Any]) -> Any:
        """Create a new record."""
        ...

    async def update(self, entity: str, record_id: str, data: dict[str, Any]) -> Optional[Any]:
        """Update an existing record."""
        ...

    async def delete(self, entity: str, record_id: str) -> bool:
        """Delete a record by ID. Returns True if deleted."""
        ...

    async def get_options(
        self,
        entity: str,
        search: Optional[str] = None,
        filters: Optional[dict] = None,
        title_field: str = "name",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get options for link field dropdowns."""
        ...
