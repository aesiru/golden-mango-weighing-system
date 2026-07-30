"""
Document Service (Application Layer)
====================================
CLEAN architecture-compliant document service.

Orchestrates document queries and link title resolution.
Delegates data access to DocumentRepository.
"""
from typing import Any, Optional, Union

from app.meta.registry import MetaRegistry
from app.infrastructure.database.repositories.document_repository import DocumentRepository


class DocumentAppService:
    """
    Application-layer document orchestration.
    
    Consolidates document_query and link_title_service functionality.
    """

    def __init__(self, document_repo: DocumentRepository):
        self._document_repo = document_repo

    # ------------------------------------------------------------------
    # Document Query Methods
    # ------------------------------------------------------------------

    def get_meta(self, entity: str) -> Optional[Any]:
        """Get entity metadata by name."""
        meta = MetaRegistry.get(entity)
        if meta is not None:
            return meta

        try:
            from app.entities import load_all_entities
            load_all_entities()
        except Exception:
            pass

        return MetaRegistry.get(entity)

    async def get_doc(
        self, entity: str, id: str, as_dict: bool = False
    ) -> Optional[Any]:
        """Fetch a document by entity name and ID."""
        return await self._document_repo.get_doc(entity, id, as_dict)

    async def get_value(
        self,
        entity: str,
        filters: Union[str, dict],
        fieldname: Union[str, list[str]],
        as_dict: bool = False,
    ) -> Optional[Any]:
        """Get a single field value or multiple field values."""
        return await self._document_repo.get_value(entity, filters, fieldname, as_dict)

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
        return await self._document_repo.get_list(
            entity, filters, fields, limit, order_by, as_dict
        )

    # ------------------------------------------------------------------
    # Link Title Resolution Methods
    # ------------------------------------------------------------------

    def _resolve_field_link(self, field) -> tuple[str | None, str | None, str | None]:
        """Return (field_name, field_type, link_entity) from a meta field object or dict."""
        if hasattr(field, "field_type"):
            field_type = field.field_type
            link_entity = getattr(field, "link_entity", None)
            child_entity = getattr(field, "child_entity", None)
            field_name = field.name
            query_key = getattr(getattr(field, "query", None), "key", None)
            if query_key is None and isinstance(getattr(field, "query", None), dict):
                query_key = (field.query or {}).get("key")
        elif isinstance(field, dict):
            field_type = field.get("field_type")
            link_entity = field.get("link_entity")
            child_entity = field.get("child_entity")
            field_name = field.get("name")
            query_key = (field.get("query") or {}).get("key")
        else:
            return None, None, None

        if field_type == "parent_child_link" and child_entity:
            link_entity = child_entity
            field_type = "link"

        if field_type == "query_link":
            if not link_entity and query_key:
                try:
                    from app.application.services.documents.query_link import QUERY_LINK_TARGET_ENTITY
                    link_entity = QUERY_LINK_TARGET_ENTITY.get(query_key)
                except Exception:
                    link_entity = None
            field_type = "link"

        if field_type != "link":
            return field_name, None, None

        return field_name, field_type, link_entity

    def inject_link_name_fields(self, meta: Any, record_dict: dict, link_titles: dict[str, str]) -> None:
        """Inject ``{field}_name`` display values into a record dict using pre-built link titles."""
        if not meta or not getattr(meta, "fields", None):
            return

        for field in meta.fields:
            field_name, field_type, link_entity = self._resolve_field_link(field)
            if field_type != "link" or not link_entity or not field_name:
                continue

            fk_value = record_dict.get(field_name)
            if not fk_value:
                continue

            name_field = f"{field_name}_name"
            if record_dict.get(name_field) not in (None, ""):
                continue

            title = link_titles.get(f"{link_entity}::{fk_value}")
            if title:
                record_dict[name_field] = title

    async def build_link_titles_batch(
        self, meta: Any, records: list[dict]
    ) -> list[dict[str, str]]:
        """Build ``_link_titles`` dict for multiple records using batch queries."""
        if not meta.fields or not records:
            return [{} for _ in records]

        entity_fk_map: dict[str, set[str]] = {}
        field_entity_map: dict[str, str] = {}

        for field in meta.fields:
            field_name, field_type, link_entity = self._resolve_field_link(field)
            if field_type != "link" or not link_entity or not field_name:
                continue

            field_entity_map[field_name] = link_entity

            fk_values = {str(r[field_name]) for r in records if r.get(field_name)}
            if fk_values:
                entity_fk_map[link_entity] = entity_fk_map.get(link_entity, set()) | fk_values

        linked_entities_data: dict[str, dict[str, str]] = {}
        for entity_name, fk_values in entity_fk_map.items():
            linked_meta = MetaRegistry.get(entity_name)
            if not linked_meta:
                continue

            title_field = linked_meta.title_field or "id"
            entity_titles = await self._document_repo.get_linked_records(
                entity_name, list(fk_values), title_field
            )
            linked_entities_data[entity_name] = entity_titles

        records_link_titles = []
        for record in records:
            link_titles: dict[str, str] = {}
            for field_name, entity_name in field_entity_map.items():
                fk_value = record.get(field_name)
                if not fk_value:
                    continue
                title = linked_entities_data.get(entity_name, {}).get(str(fk_value))
                if title:
                    link_titles[f"{entity_name}::{fk_value}"] = title
            records_link_titles.append(link_titles)

        return records_link_titles

    async def build_link_titles_single(
        self, meta: Any, record: Any
    ) -> dict[str, str]:
        """Build ``_link_titles`` dict for a single record."""
        link_titles: dict[str, str] = {}
        if not meta.fields:
            return link_titles

        for field in meta.fields:
            field_name, field_type, link_entity = self._resolve_field_link(field)
            if field_type != "link" or not link_entity or not field_name:
                continue

            fk_value = record.get(field_name) if isinstance(record, dict) else getattr(record, field_name, None)
            if not fk_value:
                continue

            linked_meta = MetaRegistry.get(link_entity)
            if not linked_meta:
                continue

            title_field = linked_meta.title_field or "id"
            title = await self._document_repo.get_linked_record(link_entity, str(fk_value), title_field)
            if title:
                link_titles[f"{link_entity}::{fk_value}"] = title

        return link_titles

    async def get_link_title(
        self, entity_name: str, record_id: str | None
    ) -> str:
        """Get display title for a single entity record."""
        if not record_id:
            return ""

        meta = MetaRegistry.get(entity_name)
        title_field = meta.title_field if meta else "id"

        doc = await self.get_doc(entity_name, str(record_id), as_dict=True)
        if not doc:
            return str(record_id)

        value = doc.get(title_field)
        if value in (None, ""):
            return str(record_id)

        return str(value)

    async def get_record_display_name(
        self, entity_name: str, record: Any
    ) -> str:
        """Get display name for a record (title field or ID)."""
        if record is None:
            return ""

        meta = MetaRegistry.get(entity_name)
        title_field = meta.title_field if meta else "id"

        if isinstance(record, dict):
            title_value = record.get(title_field)
            if title_value not in (None, ""):
                return str(title_value)
            record_id = record.get("id")
            if record_id and title_field != "id":
                return await self.get_link_title(entity_name, str(record_id))
            return str(record_id or "")

        title_value = getattr(record, title_field, None)
        if title_value not in (None, ""):
            return str(title_value)

        record_id = getattr(record, "id", None)
        if record_id and title_field != "id":
            return await self.get_link_title(entity_name, str(record_id))

        return str(record_id or "")
