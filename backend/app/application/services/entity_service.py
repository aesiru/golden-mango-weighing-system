"""
Entity Service
===============
Orchestrates generic CRUD operations for all entities.
Delegates data access to EntityRepository, hooks to HookRegistry.
"""
from typing import Any, Optional
from datetime import datetime, date

from app.core.serialization import record_to_dict
from app.meta.registry import MetaRegistry
from app.domain.exceptions import (
    EntityNotFoundError, PermissionDeniedError, ValidationError,
)


class EntityService:
    """Application-layer orchestration for entity CRUD."""

    def __init__(self, entity_repo, naming_repo, rbac_service, workflow_repo, socket_manager):
        self.entity_repo = entity_repo
        self.naming_repo = naming_repo
        self.rbac = rbac_service
        self.workflow_repo = workflow_repo
        self.socket_manager = socket_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_meta(self, entity: str):
        meta = MetaRegistry.get(entity)
        if not meta:
            raise EntityNotFoundError("Entity", entity)
        return meta

    @staticmethod
    def coerce_incoming_types(model: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce incoming request values based on SQLAlchemy column types."""
        if not data:
            return data

        from sqlalchemy.sql.sqltypes import String, Text, DateTime, Date, Integer, Float, BigInteger, SmallInteger, Numeric, DECIMAL, REAL

        cols = getattr(model, "__table__").columns
        out = dict(data)
        for key, value in list(out.items()):
            if key not in cols:
                continue
            col = cols[key]

            if value in (None, ""):
                if col.nullable:
                    out[key] = None
                elif value == "" and isinstance(col.type, (String, Text)):
                    out[key] = ""
                continue

            # Handle numeric types - convert strings to numbers
            if isinstance(col.type, (Integer, BigInteger, SmallInteger)) and isinstance(value, str):
                try:
                    out[key] = int(value)
                except (ValueError, TypeError):
                    pass  # Keep original value if conversion fails

            elif isinstance(col.type, (Float, Numeric, DECIMAL, REAL)) and isinstance(value, str):
                try:
                    out[key] = float(value)
                except (ValueError, TypeError):
                    pass  # Keep original value if conversion fails

            elif isinstance(col.type, DateTime) and isinstance(value, str):
                v = value.strip()
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                try:
                    out[key] = datetime.fromisoformat(v)
                except ValueError:
                    pass

            elif isinstance(col.type, Date) and isinstance(value, str):
                v = value.strip()
                try:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    out[key] = dt.date()
                except ValueError:
                    try:
                        out[key] = date.fromisoformat(v)
                    except ValueError:
                        pass
        return out

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_detail(self, entity: str, record_id: str) -> dict:
        meta = self._get_meta(entity)
        record = await self.entity_repo.get_by_id(entity, record_id)
        if not record:
            raise EntityNotFoundError(meta.label, record_id)
        return record_to_dict(record)

    async def get_list(
        self,
        entity: str,
        page: int = 1,
        page_size: int = 20,
        sort_field: Optional[str] = None,
        sort_order: str = "desc",
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None,
    ) -> dict:
        self._get_meta(entity)
        filters = {}
        if filter_field and filter_value is not None:
            filters[filter_field] = filter_value

        records, total = await self.entity_repo.get_list(
            entity,
            filters=filters if filters else None,
            order_by=sort_field,
            order_dir=sort_order,
            page=page,
            page_size=page_size,
        )
        return {"data": records, "total": total, "page": page, "page_size": page_size}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, entity: str, data: dict[str, Any], user: Any) -> Any:
        meta = self._get_meta(entity)
        model = self.entity_repo.get_model(entity)
        if not model:
            raise EntityNotFoundError("Model", entity)

        # Generate ID if naming enabled
        if meta.naming and meta.naming.enabled and not data.get("id"):
            generated_id = await self.naming_repo.get_next_id(
                meta.naming.prefix, meta.naming.digits
            )
            data["id"] = generated_id

        # Set initial workflow state if workflow is enabled
        if meta.workflow and meta.workflow.enabled and not data.get("workflow_state"):
            data["workflow_state"] = meta.workflow.initial_state

        data = self.coerce_incoming_types(model, data)
        record = await self.entity_repo.create(entity, data)
        return record

    async def update(self, entity: str, record_id: str, data: dict[str, Any], user: Any) -> Any:
        meta = self._get_meta(entity)
        model = self.entity_repo.get_model(entity)
        if not model:
            raise EntityNotFoundError("Model", entity)

        data = self.coerce_incoming_types(model, data)

        # Strip system fields
        system_fields = {"id", "created_at", "updated_at"}
        clean_data = {k: v for k, v in data.items() if k not in system_fields}

        record = await self.entity_repo.update(entity, record_id, clean_data)
        if not record:
            raise EntityNotFoundError(meta.label, record_id)
        return record

    async def delete(self, entity: str, record_id: str, user: Any) -> bool:
        meta = self._get_meta(entity)
        deleted = await self.entity_repo.delete(entity, record_id)
        if not deleted:
            raise EntityNotFoundError(meta.label, record_id)
        return True

    async def bulk_delete(self, entity: str, record_ids: list[str], user: Any) -> dict[str, Any]:
        """Delete multiple records for an entity.

        Returns:
            dict: {
                'deleted_count': int,
                'failed_count': int,
                'failed_deletions': list[dict],  # Each contains: {'id': str, 'error': str, 'error_type': str}
                'error_summary': dict[str, int]  # Error type to count mapping
            }
        """
        meta = self._get_meta(entity)
        deleted_count, failed_deletions, error_summary = await self.entity_repo.bulk_delete(entity, record_ids)

        return {
            'deleted_count': deleted_count,
            'failed_count': len(failed_deletions),
            'failed_deletions': failed_deletions,
            'error_summary': error_summary,
        }
