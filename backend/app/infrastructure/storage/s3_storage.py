"""
S3 Storage Backend (stub)
==========================
Swap-in replacement for LocalStorageBackend when STORAGE_BACKEND=s3.
Requires: boto3, and the following settings:
  S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

Install boto3 before use:
    pip install boto3
"""
from __future__ import annotations

import mimetypes
import uuid

from app.infrastructure.storage.base import StoredFile


class S3StorageBackend:
    """AWS S3-backed storage.  Not yet wired — add real bucket settings first."""

    def __init__(self) -> None:
        from app.core.config import settings

        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 storage. Run: pip install boto3"
            ) from exc

        self._bucket: str = getattr(settings, "S3_BUCKET", "")
        if not self._bucket:
            raise RuntimeError("S3_BUCKET must be set when STORAGE_BACKEND=s3")

        self._client = boto3.client(
            "s3",
            region_name=getattr(settings, "AWS_REGION", "us-east-1"),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )

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
        ext = "".join(c for c in ext if c.isalnum())[:10]

        file_id = str(uuid.uuid4())
        stored_name = f"{file_id}.{ext}" if ext else file_id
        object_key = f"{entity}/{record_id}/{stored_name}"

        resolved_mime = mime_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

        self._client.put_object(
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
            ContentType=resolved_mime,
        )

        return StoredFile(
            file_id=file_id,
            stored_name=stored_name,
            file_path=object_key,  # S3 object key used as "file_path"
            file_size=len(content),
            mime_type=resolved_mime,
        )

    async def delete(self, file_path: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=file_path)
        except Exception:  # noqa: BLE001
            pass

    def public_url(self, file_path: str, original_name: str) -> str | None:
        """Generate a 1-hour presigned download URL."""
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": file_path},
                ExpiresIn=3600,
            )
        except Exception:  # noqa: BLE001
            return None
