"""
Storage Infrastructure
======================
Pluggable file storage layer. Default: local disk.
Swap to S3 by setting STORAGE_BACKEND=s3 in environment.
"""
from app.infrastructure.storage.base import StorageBackend, StoredFile
from app.infrastructure.storage.local_storage import LocalStorageBackend

__all__ = ["StorageBackend", "StoredFile", "LocalStorageBackend", "get_storage"]


def get_storage() -> StorageBackend:
    """Return the configured storage backend (injected into routes via DI)."""
    from app.core.config import settings

    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend == "s3":
        from app.infrastructure.storage.s3_storage import S3StorageBackend
        return S3StorageBackend()
    return LocalStorageBackend()
