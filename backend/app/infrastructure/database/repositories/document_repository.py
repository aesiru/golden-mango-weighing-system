"""
Document Repository
===================
Concrete SQLAlchemy implementation for document data access.
"""
from typing import Any, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.meta.registry import MetaRegistry
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.infrastructure.database.query.filter_builder import build_filter_condition


class DocumentRepository:
    """Concrete document repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._model_cache: dict[str, Any] = {}

    def _get_model(self, entity: str) -> Optional[Any]:
        """Get SQLAlchemy model class by entity name."""
        if entity in self._model_cache:
            return self._model_cache[entity]

        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if hasattr(cls, "__tablename__") and cls.__tablename__ == entity:
                self._model_cache[entity] = cls
                return cls

        return None

    async def get_doc(
        self, entity: str, id: str, as_dict: bool = False
    ) -> Optional[Any]:
        """Fetch a document by entity name and ID."""
        model = self._get_model(entity)
        if not model:
            return None

        result = await self.db.execute(select(model).where(model.id == id))
        doc = result.scalar_one_or_none()

        if doc and as_dict:
            from app.core.serialization import record_to_dict
            return record_to_dict(doc)

        return doc

    async def get_value(
        self,
        entity: str,
        filters: Union[str, dict],
        fieldname: Union[str, list[str]],
        as_dict: bool = False,
    ) -> Optional[Any]:
        """Get a single field value or multiple field values."""
        model = self._get_model(entity)
        if not model:
            return None

        query = select(model)

        if isinstance(filters, str):
            query = query.where(model.id == filters)
        elif isinstance(filters, dict):
            for field, value in filters.items():
                if hasattr(model, field):
                    condition = build_filter_condition(getattr(model, field), value)
                    if condition is not None:
                        query = query.where(condition)

        result = await self.db.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            return None

        from app.core.serialization import record_to_dict

        if fieldname == "*":
            return record_to_dict(doc)

        if isinstance(fieldname, str):
            return getattr(doc, fieldname, None)

        if isinstance(fieldname, list):
            if as_dict:
                return {f: getattr(doc, f, None) for f in fieldname}
            return tuple(getattr(doc, f, None) for f in fieldname)

        return None

    async def get_list(
        self,
        entity: str,
        filters: Optional[dict] = None,
        fields: Union[str, list[str]] = "*",
        limit: int = 0,
        order_by: Optional[str] = None,
        as_dict: bool = True,
    ) -> list[Any]:
        """Fetch a list of documents matching filters."""
        model = self._get_model(entity)
        if not model:
            return []

        query = select(model)

        if filters:
            for field, value in filters.items():
                if hasattr(model, field):
                    condition = build_filter_condition(getattr(model, field), value)
                    if condition is not None:
                        query = query.where(condition)

        if order_by and hasattr(model, order_by):
            query = query.order_by(getattr(model, order_by))

        if limit > 0:
            query = query.limit(limit)

        result = await self.db.execute(query)
        docs = result.scalars().all()

        if not as_dict:
            return docs

        from app.core.serialization import record_to_dict

        out = []
        for doc in docs:
            if fields == "*":
                out.append(record_to_dict(doc))
            elif isinstance(fields, list):
                item = {}
                for f in fields:
                    item[f] = getattr(doc, f, None)
                out.append(item)

        return out

    async def get_latest_id_for_prefix(self, entity: str, prefix: str) -> Optional[str]:
        """Get the latest ID for a given prefix."""
        model = self._get_model(entity)
        if not model:
            return None

        prefix_like = f"{prefix}-%"
        result = await self.db.execute(
            select(model.id)
            .where(model.id.like(prefix_like))
            .order_by(model.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_linked_records(
        self, entity: str, ids: list[str], title_field: str = "id"
    ) -> dict[str, str]:
        """Get linked records by IDs for title resolution."""
        model = self._get_model(entity)
        if not model:
            return {}

        result = await self.db.execute(
            select(model).where(model.id.in_(ids))
        )
        entity_titles = {}
        for rec in result.scalars().all():
            rec_id = str(getattr(rec, "id", None))
            entity_titles[rec_id] = str(getattr(rec, title_field, None) or rec_id)
        return entity_titles

    async def get_linked_record(
        self, entity: str, id: str, title_field: str = "id"
    ) -> Optional[str]:
        """Get a single linked record for title resolution."""
        model = self._get_model(entity)
        if not model:
            return None

        result = await self.db.execute(
            select(model).where(model.id == id)
        )
        linked_record = result.scalar_one_or_none()
        if linked_record:
            return str(getattr(linked_record, title_field, None) or id)
        return None
