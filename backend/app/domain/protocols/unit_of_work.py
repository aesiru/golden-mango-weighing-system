"""
Unit of Work Protocol
=====================
Abstract interface for transactional boundaries.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    """Interface for managing database transactions."""

    async def __aenter__(self) -> 'UnitOfWorkProtocol':
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
