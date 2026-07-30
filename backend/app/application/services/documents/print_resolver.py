"""
Application Layer: Print Resolver

Resolves link display names for print templates.
Wraps DocumentAppService to provide async resolution of link titles.

Clean Architecture Layer: Application
Responsibility: Resolve link display names for print document generation
"""
from __future__ import annotations

from typing import Optional
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document_service import DocumentAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository


async def resolve_link_display(
    entity_name: str,
    record_id: Optional[str],
    db: AsyncSession,
) -> str:
    """Resolve a single link display name for an entity record."""
    document_repo = DocumentRepository(db)
    document_service = DocumentAppService(document_repo)
    return await document_service.get_link_title(entity_name, record_id)


async def resolve_many_link_displays(
    entity_name: str,
    record_ids: list[str],
    db: AsyncSession,
) -> dict[str, str]:
    """Resolve multiple link display names for an entity in parallel."""
    unique_ids = sorted({rid for rid in record_ids if rid})
    if not unique_ids:
        return {}

    results = await asyncio.gather(
        *[resolve_link_display(entity_name, rid, db) for rid in unique_ids],
        return_exceptions=True,
    )

    out: dict[str, str] = {}
    for rid, result in zip(unique_ids, results):
        if isinstance(result, Exception):
            out[rid] = rid
        else:
            out[rid] = result

    return out
