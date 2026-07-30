"""
Naming Repository
==================
Concrete SQLAlchemy implementation for naming series data access.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.infrastructure import Series


class NamingRepository:
    """Concrete naming repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_next_id(self, prefix: str, digits: int) -> str:
        result = await self.db.execute(select(Series).where(Series.name == prefix))
        series = result.scalar_one_or_none()

        if not series:
            series = Series(name=prefix, current=0)
            self.db.add(series)

        series.current += 1
        await self.db.flush()

        return f"{prefix}-{str(series.current).zfill(digits)}"

    async def get_current_value(self, prefix: str) -> Optional[int]:
        result = await self.db.execute(select(Series).where(Series.name == prefix))
        series = result.scalar_one_or_none()
        return series.current if series else None

    async def set_current_value(self, prefix: str, value: int) -> None:
        """Force the series counter for *prefix* to *value*.

        Used by NamingAppService to re-sync the in-DB counter when existing
        records have higher IDs than what the Series table tracks.
        """
        result = await self.db.execute(select(Series).where(Series.name == prefix))
        series = result.scalar_one_or_none()
        if series is None:
            series = Series(name=prefix, current=value)
            self.db.add(series)
        else:
            series.current = value
        await self.db.flush()

    async def get_latest_id_for_prefix(self, entity: str, prefix: str) -> Optional[str]:
        """Return the highest existing ID for *entity* that starts with *prefix*.

        Queries the entity's own table so the naming series stays in sync with
        actual data even after manual imports or DB restores.
        Returns None when the entity model is not found or has no rows yet.
        """
        # Late import to avoid circular dependency at module load time.
        from app.infrastructure.database.repositories.entity_repository import get_entity_model
        from sqlalchemy import desc, text

        model = get_entity_model(entity)
        if model is None or not hasattr(model, "id"):
            return None
        try:
            result = await self.db.execute(
                select(model.id)
                .where(model.id.like(f"{prefix}-%"))
                .order_by(desc(model.id))
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None
