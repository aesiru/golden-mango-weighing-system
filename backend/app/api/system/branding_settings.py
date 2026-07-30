from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.branding_service import BrandingService
from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user_from_token
from app.infrastructure.settings import BrandingStore

router = APIRouter(tags=["branding-settings"])


class BrandingSettingsUpdate(BaseModel):
    organization_name: str
    description: str | None = None


def get_branding_service() -> BrandingService:
    uploads_root = Path(settings.UPLOAD_DIR)
    settings_dir = uploads_root / "settings"
    return BrandingService(
        store=BrandingStore(settings_dir / "branding.json"),
        assets_dir=settings_dir / "branding",
        uploads_root=uploads_root,
    )


def _ensure_superuser(current_user: CurrentUser) -> None:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/settings/branding")
async def get_branding_settings(
    _db: AsyncSession = Depends(get_db),
):
    service = get_branding_service()
    return {"status": "success", "data": service.get_branding()}


@router.put("/settings/branding")
async def update_branding_settings(
    payload: BrandingSettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user_from_token),
    _db: AsyncSession = Depends(get_db),
):
    _ensure_superuser(current_user)
    service = get_branding_service()
    data = service.save_branding(payload.organization_name, payload.description)
    return {"status": "success", "message": "Branding settings updated", "data": data}


@router.post("/settings/branding/logo")
async def upload_branding_logo(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    _db: AsyncSession = Depends(get_db),
):
    _ensure_superuser(current_user)

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    service = get_branding_service()
    data = service.save_logo(content, file.filename or "logo", file.content_type)
    return {"status": "success", "message": "Logo uploaded", "data": data}


@router.delete("/settings/branding/logo")
async def delete_branding_logo(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    _db: AsyncSession = Depends(get_db),
):
    _ensure_superuser(current_user)
    service = get_branding_service()
    data = service.remove_logo()
    return {"status": "success", "message": "Logo removed", "data": data}
