"""
Cache Protocol
==============
Abstract interface for caching implementations.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class CacheProtocol(Protocol):
    """Interface for cache implementations (in-memory, Redis, etc.)."""

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key."""
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL in seconds."""
        ...

    def delete(self, key: str) -> None:
        """Remove a cached value."""
        ...

    def clear(self) -> None:
        """Flush all cached entries."""
        ...
