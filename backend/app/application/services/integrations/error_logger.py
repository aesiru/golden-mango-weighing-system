"""Error logging helper that persists exception details to the Error Log entity."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.meta.registry import MetaRegistry
from app.core.framework.models.infrastructure import ErrorLog
from app.application.services.documents.naming_service import NamingAppService
from app.infrastructure.database.repositories.naming_repository import NamingRepository

logger = logging.getLogger(__name__)


async def _build_error_log_instance(
    db: AsyncSession,
    status: Optional[int],
    title: Optional[str],
    message: Optional[str],
) -> ErrorLog:
    meta = MetaRegistry.get("error_log")
    generated_id: Optional[str] = None

    if meta and meta.naming and meta.naming.enabled:
        naming_repo = NamingRepository(db)
        naming_service = NamingAppService(naming_repo)
        generated_id = await naming_service.generate_id(meta.naming)

    return ErrorLog(
        id=generated_id or f"ERR-{uuid.uuid4()}",
        status=status,
        title=title,
        message=message,
    )


async def log_error(status: Optional[int], title: Optional[str], message: Optional[str]) -> None:
    """Persist an error entry. Failures are swallowed but logged."""
    try:
        async with async_session_maker() as db:
            error_log = await _build_error_log_instance(db, status, title, message)
            db.add(error_log)
            await db.commit()
    except Exception:
        logger.exception("Failed to persist error log entry")
