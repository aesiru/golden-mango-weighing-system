from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.protocols.fetch_from_repository import FetchFromRepositoryProtocol
from app.infrastructure.database.repositories.entity_repository import get_entity_model


class FetchFromRepository(FetchFromRepositoryProtocol):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_partial_fields(
        self,
        entity: str,
        record_id: str,
        fields: list[str],
    ) -> Optional[dict[str, Any]]:
        model = get_entity_model(entity)
        if not model:
            return None

        result = await self.db.execute(select(model).where(model.id == record_id))
        record = result.scalar_one_or_none()
        if not record:
            return None

        out: dict[str, Any] = {}
        for f in fields:
            out[f] = getattr(record, f, None)
        return out

    async def get_title(
        self,
        entity: str,
        record_id: str,
        title_field: str,
    ) -> Optional[str]:
        model = get_entity_model(entity)
        if not model:
            return None

        result = await self.db.execute(select(model).where(model.id == record_id))
        record = result.scalar_one_or_none()
        if not record:
            return None

        v = getattr(record, title_field, None)
        return str(v) if v is not None else None
