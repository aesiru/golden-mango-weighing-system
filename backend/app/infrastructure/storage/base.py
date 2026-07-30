"""
Storage Backend Protocol
========================
All concrete storage implementations must satisfy this interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class StoredFile:
    """Immutable value object returned after a successful store operation."""
    file_id: str          # UUID without extension
    stored_name: str      # UUID + extension, e.g. "abc.pdf"
    file_path: str        # Absolute path (local) or object key (S3)
    file_size: int        # Bytes
    mime_type: str


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol every storage backend must implement."""

    async def save(
        self,
        *,
        content: bytes,
        original_name: str,
        entity: str,
        record_id: str,
        mime_type: str,
    ) -> StoredFile:
        """Persist *content* and return a StoredFile descriptor."""
        ...

    async def delete(self, file_path: str) -> None:
        """Remove the file at *file_path* (best-effort; never raises on missing)."""
        ...

    def public_url(self, file_path: str, original_name: str) -> str | None:
        """Return a presigned / public URL suitable for download, or None."""
        ...
