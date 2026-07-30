"""
Entity Repository
==================
Concrete SQLAlchemy implementation of EntityRepositoryProtocol.
Extracts model lookup and generic CRUD from routers/entity.py and services/document.py.
"""
from typing import Any, Optional, Union
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.infrastructure.database.query.filter_builder import build_filter_condition
from app.core.serialization import record_to_dict


# Model cache for dynamic lookups
_MODEL_CACHE: dict[str, Any] = {}

# Pre-registered models (core models that aren't in modules)
_REGISTERED_MODELS: dict[str, Any] = {}


def register_model(entity_name: str, model_class: Any):
    """Register a model class for an entity name."""
    _REGISTERED_MODELS[entity_name] = model_class


def get_entity_model(entity: str) -> Optional[Any]:
    """Get SQLAlchemy model class by entity name.

    Lookup order:
    1. Pre-registered models (core auth/workflow models)
    2. Cache from previous lookups
    3. Dynamic scan of Base.registry.mappers (by __tablename__)
    """
    if entity in _REGISTERED_MODELS:
        return _REGISTERED_MODELS[entity]

    if entity in _MODEL_CACHE:
        return _MODEL_CACHE[entity]

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, "__tablename__") and cls.__tablename__ == entity:
            _MODEL_CACHE[entity] = cls
            return cls

    return None


def register_core_models():
    """Register core models that live outside modules.

    Called once during app startup after models are imported.
    """
    from app.core.framework.models.auth import User, Role, EntityPermission
    from app.core.framework.models.infrastructure import (
        ErrorLog, AuditLog, Attachment, EmailLog,
        NotificationSubscription, ScheduledJobLog, UserActivity, Series,
    )
    from app.core.framework.models.ordering import ModuleOrder, EntityOrder
    from app.core.framework.models.workflow import (
        Workflow, WorkflowState, WorkflowAction,
        WorkflowStateLink, WorkflowTransition,
    )

    for name, cls in {
        # Auth
        "user": User,
        "role": Role,
        "entity_permission": EntityPermission,
        # Infrastructure
        "error_log": ErrorLog,
        "audit_log": AuditLog,
        "attachment": Attachment,
        "email_log": EmailLog,
        "notification_subscription": NotificationSubscription,
        "scheduled_job_log": ScheduledJobLog,
        "user_activity": UserActivity,
        "series": Series,
        # Ordering
        "module_order": ModuleOrder,
        "entity_order": EntityOrder,
        # Workflow
        "workflow": Workflow,
        "workflow_state": WorkflowState,
        "workflow_action": WorkflowAction,
        "workflow_state_link": WorkflowStateLink,
        "workflow_transition": WorkflowTransition,
    }.items():
        register_model(name, cls)


class EntityRepository:
    """Concrete entity repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Model lookup
    # ------------------------------------------------------------------

    def get_model(self, entity: str) -> Optional[Any]:
        return get_entity_model(entity)

    # ------------------------------------------------------------------
    # Single record
    # ------------------------------------------------------------------

    async def get_by_id(self, entity: str, record_id: str) -> Optional[Any]:
        model = self.get_model(entity)
        if not model:
            return None
        result = await self.db.execute(select(model).where(model.id == record_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Paginated list
    # ------------------------------------------------------------------

    async def get_list(
        self,
        entity: str,
        filters: Optional[dict] = None,
        search: Optional[str] = None,
        search_fields: Optional[list[str]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        model = self.get_model(entity)
        if not model:
            return [], 0

        query = select(model)
        count_query = select(func.count()).select_from(model)

        # Apply filters
        if filters:
            for field_name, value in filters.items():
                if hasattr(model, field_name) and value is not None:
                    condition = build_filter_condition(getattr(model, field_name), value)
                    if condition is not None:
                        query = query.where(condition)
                        count_query = count_query.where(condition)

        # Apply search
        if search and search_fields:
            from sqlalchemy import or_
            conditions = []
            for sf in search_fields:
                if hasattr(model, sf):
                    conditions.append(getattr(model, sf).ilike(f"%{search}%"))
            if conditions:
                query = query.where(or_(*conditions))
                count_query = count_query.where(or_(*conditions))

        # Count
        total = (await self.db.execute(count_query)).scalar() or 0

        # Order
        if order_by and hasattr(model, order_by):
            col = getattr(model, order_by)
            query = query.order_by(col.desc() if order_dir == "desc" else col.asc())

        # Paginate
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        records = [record_to_dict(r) for r in result.scalars().all()]
        return records, total

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(self, entity: str, data: dict[str, Any]) -> Any:
        model = self.get_model(entity)
        if not model:
            return None
        record = model(**data)
        self.db.add(record)
        await self.db.flush()
        return record

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(self, entity: str, record_id: str, data: dict[str, Any]) -> Optional[Any]:
        record = await self.get_by_id(entity, record_id)
        if not record:
            return None
        for key, value in data.items():
            if key in {"id", "created_at", "updated_at", "created_by"}:
                continue
            if hasattr(record, key):
                setattr(record, key, value)
        await self.db.flush()
        return record

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, entity: str, record_id: str) -> bool:
        record = await self.get_by_id(entity, record_id)
        if not record:
            return False
        await self.db.delete(record)
        await self.db.flush()
        return True

    async def bulk_delete(self, entity: str, record_ids: list[str]) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
        """Delete multiple records with individual transactions for each.

        Returns:
            tuple: (number_of_deleted_records, list_of_failed_deletions, error_summary)
                   Failed deletions contain: {'id': str, 'error': str, 'error_type': str}
                   Error summary contains: {'error_type': count} for aggregation
        """
        model = self.get_model(entity)
        if not model:
            error_summary = {'Model not found': len(record_ids)}
            return 0, [{'id': id, 'error': f'Model for entity {entity} not found', 'error_type': 'Model not found'} for id in record_ids], error_summary

        deleted_count = 0
        failed_deletions: list[dict[str, Any]] = []
        error_summary: dict[str, int] = {}

        for record_id in record_ids:
            # Use a nested transaction (savepoint) for each record to allow partial success
            savepoint = await self.db.begin_nested()
            try:
                record = await self.get_by_id(entity, record_id)
                if not record:
                    error_type = 'Record not found'
                    failed_deletions.append({'id': record_id, 'error': 'Record not found', 'error_type': error_type})
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1
                    await savepoint.rollback()
                    continue

                await self.db.delete(record)
                await self.db.flush()
                deleted_count += 1
                await savepoint.commit()
            except Exception as e:
                await savepoint.rollback()
                error_msg = str(e)

                # Check if it's a foreign key violation
                from sqlalchemy.exc import IntegrityError
                if isinstance(e, IntegrityError) and "foreign key constraint" in error_msg.lower():
                    error_type = 'Foreign key constraint violation'
                    failed_deletions.append({
                        'id': record_id,
                        'error': error_type,
                        'error_type': error_type
                    })
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1
                else:
                    error_type = 'Other error'
                    failed_deletions.append({'id': record_id, 'error': error_msg, 'error_type': error_type})
                    error_summary[error_type] = error_summary.get(error_type, 0) + 1

        return deleted_count, failed_deletions, error_summary

    # ------------------------------------------------------------------
    # Options (for link dropdowns)
    # ------------------------------------------------------------------

    async def get_options(
        self,
        entity: str,
        search: Optional[str] = None,
        filters: Optional[dict] = None,
        title_field: str = "name",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        model = self.get_model(entity)
        if not model:
            return []

        query = select(model)

        if filters:
            for field_name, value in filters.items():
                if hasattr(model, field_name) and value is not None:
                    condition = build_filter_condition(getattr(model, field_name), value)
                    if condition is not None:
                        query = query.where(condition)

        if search and hasattr(model, title_field):
            query = query.where(getattr(model, title_field).ilike(f"%{search}%"))

        query = query.limit(limit)
        result = await self.db.execute(query)
        records = result.scalars().all()

        options = []
        for r in records:
            label = getattr(r, title_field, None) or getattr(r, "id", "")
            options.append({"value": r.id, "label": str(label)})
        return options

    # ------------------------------------------------------------------
    # Find referencing records
    # ------------------------------------------------------------------

    async def find_referencing_records(
        self,
        entity: str,
        record_id: str,
    ) -> list[dict[str, Any]]:
        """Find all records that reference a given entity record via foreign keys.

        Returns a list of dictionaries with:
        - entity: the referencing entity name
        - id: the referencing record ID
        - field: the foreign key field name
        """
        model = self.get_model(entity)
        if not model:
            return []

        referencing_records = []

        # Iterate through all registered models to find foreign key references
        for mapper in Base.registry.mappers:
            ref_model = mapper.class_
            if not hasattr(ref_model, "__tablename__"):
                continue

            # Skip the same model
            if ref_model.__tablename__ == entity:
                continue

            # Check all columns for foreign keys to the target entity
            for column in ref_model.__table__.columns:
                for fk in column.foreign_keys:
                    if fk.column.table.name == entity:
                        # Found a foreign key reference
                        try:
                            field_name = column.name
                            query = select(ref_model).where(getattr(ref_model, field_name) == record_id)
                            result = await self.db.execute(query)
                            records = result.scalars().all()

                            for record in records:
                                # Try to get a display name for the record
                                display_name = getattr(record, "name", None)
                                if not display_name:
                                    display_name = getattr(record, "description", None)
                                if not display_name:
                                    display_name = getattr(record, "id", "")

                                # Make entity name human-readable
                                entity_name = ref_model.__tablename__.replace("_", " ").title()

                                referencing_records.append({
                                    "entity": ref_model.__tablename__,
                                    "entity_display": entity_name,
                                    "id": record.id,
                                    "field": field_name,
                                    "display_name": str(display_name),
                                })
                        except Exception:
                            # Skip if query fails (e.g., field doesn't exist on model)
                            pass

        return referencing_records
