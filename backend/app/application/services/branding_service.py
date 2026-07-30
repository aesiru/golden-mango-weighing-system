from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Any

from app.domain.protocols.branding_store import BrandingStoreProtocol


class BrandingService:
    DEFAULTS = {
        "organization_name": "My App",
        "description": "A modular FastAPI + Nuxt application",
        "logo_url": None,
    }

    def __init__(self, store: BrandingStoreProtocol, assets_dir: Path, uploads_root: Path):
        self.store = store
        self.assets_dir = assets_dir
        self.uploads_root = uploads_root
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def get_branding(self) -> dict[str, Any]:
        data = self.store.load()
        return {**self.DEFAULTS, **data}

    def save_branding(self, organization_name: str, description: str | None) -> dict[str, Any]:
        current = self.get_branding()
        current["organization_name"] = organization_name.strip()
        current["description"] = (description or "").strip()
        return self.store.save(current)

    def save_logo(self, content: bytes, original_name: str, content_type: str | None) -> dict[str, Any]:
        ext = Path(original_name).suffix.lower()
        if not ext:
            guessed_ext = mimetypes.guess_extension(content_type or "") or ".bin"
            ext = guessed_ext.lower()

        for existing in self.assets_dir.glob("logo.*"):
            existing.unlink(missing_ok=True)

        file_name = f"logo-{uuid.uuid4().hex[:8]}{ext}"
        file_path = self.assets_dir / file_name
        file_path.write_bytes(content)

        relative = file_path.relative_to(self.uploads_root)
        logo_url = f"/uploads/{relative.as_posix()}"

        current = self.get_branding()
        current["logo_url"] = logo_url
        self.store.save(current)
        return current

    def remove_logo(self) -> dict[str, Any]:
        current = self.get_branding()
        for existing in self.assets_dir.glob("logo-*"):
            existing.unlink(missing_ok=True)
        current["logo_url"] = None
        return self.store.save(current)
