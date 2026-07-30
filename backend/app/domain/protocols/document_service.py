"""
Document Service Protocol
=========================
Abstract interface for document query and mutation operations.
Services depend on this protocol, not concrete implementations.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class DocumentQueryProtocol(Protocol):
    """Read-only document operations."""

    async def get_doc(
        self, entity: str, id: str, db: Any, as_dict: bool = False
    ) -> Optional[Any]: ...

    async def get_list(
        self, entity: str, db: Any, **kwargs: Any
    ) -> dict: ...


@runtime_checkable
class DocumentMutationProtocol(Protocol):
    """Write document operations."""

    async def new_doc(self, entity: str, data: dict, db: Any) -> Any: ...

    async def save_doc(self, doc: Any, db: Any, commit: bool = True) -> Any: ...

    async def delete_doc(self, entity: str, id: str, db: Any) -> bool: ...
