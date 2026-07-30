"""
Local Disk Storage Backend
===========================
Stores files under UPLOAD_DIR/<entity>/<record_id>/<uuid>.<ext>.
This is the default backend for development and self-hosted deployments.
"""
from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

from app.infrastructure.storage.base import StoredFile


class LocalStorageBackend:
    """Concrete local-disk implementation of StorageBackend."""

    def __init__(self, root: str | Path | None = None) -> None:
        if root is None:
            from app.core.config import settings
            root = settings.UPLOAD_DIR
        self._root = Path(root)

    async def save(
        self,
        *,
        content: bytes,
        original_name: str,
        entity: str,
        record_id: str,
        mime_type: str,
    ) -> StoredFile:
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        # Sanitize extension — only allow alphanumeric chars to prevent path traversal
        ext = "".join(c for c in ext if c.isalnum())[:10]

        file_id = str(uuid.uuid4())
        stored_name = f"{file_id}.{ext}" if ext else file_id

        dest_dir = self._root / entity / record_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / stored_name

        with open(file_path, "wb") as fh:
            fh.write(content)

        resolved_mime = mime_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

        return StoredFile(
            file_id=file_id,
            stored_name=stored_name,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=resolved_mime,
        )

    async def delete(self, file_path: str) -> None:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    def public_url(self, file_path: str, original_name: str) -> str | None:
        # Local storage serves files through the /uploads static mount in main.py.
        # Compute a relative URL from the upload root.
        try:
            from app.core.config import settings
            rel = Path(file_path).relative_to(Path(settings.UPLOAD_DIR))
            return f"/uploads/{rel.as_posix()}"
        except ValueError:
            return None
