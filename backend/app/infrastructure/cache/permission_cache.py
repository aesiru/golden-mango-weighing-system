"""
Permission Cache
================
Extracted RBAC permission cache (was embedded in services/rbac.py).
Implements CacheProtocol for dependency inversion.

Uses TTL-based expiration so permission DB queries are avoided for
repeat requests within the TTL window (default 60 seconds).
"""
import time
from typing import Optional


_DEFAULT_TTL = 60  # seconds


class PermissionCache:
    """In-memory permission cache keyed by role_id:entity_name with TTL."""

    def __init__(self, ttl_seconds: float = _DEFAULT_TTL) -> None:
        self._store: dict[str, tuple[dict[str, bool], float]] = {}
        self._ttl = ttl_seconds

    def get(self, role_id: str, entity_name: str) -> Optional[dict[str, bool]]:
        """Return cached permission dict or None if missing/expired."""
        entry = self._store.get(f"{role_id}:{entity_name}")
        if entry is None:
            return None
        perms, expires_at = entry
        if time.monotonic() >= expires_at:
            del self._store[f"{role_id}:{entity_name}"]
            return None
        return perms

    def set(self, role_id: str, entity_name: str, perms: dict[str, bool]) -> None:
        """Store permission dict with TTL."""
        self._store[f"{role_id}:{entity_name}"] = (perms, time.monotonic() + self._ttl)

    def clear(self) -> None:
        """Flush all cached entries."""
        self._store.clear()

    def __contains__(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        _, expires_at = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return False
        return True


# Singleton instance
permission_cache = PermissionCache()
