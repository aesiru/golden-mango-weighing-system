from typing import Any, Optional

from app.meta.registry import MetaRegistry
from app.domain.protocols.fetch_from_repository import FetchFromRepositoryProtocol


class FetchFromService:
    def __init__(self, repo: FetchFromRepositoryProtocol):
        self.repo = repo

    async def get_fetch_from_fields(
        self,
        entity: str,
        record_id: str,
        fields: list[str],
    ) -> tuple[Optional[dict[str, Any]], dict[str, str]]:
        meta = MetaRegistry.get(entity)
        if not meta:
            return None, {}

        data = await self.repo.get_partial_fields(entity, record_id, fields)
        if data is None:
            return None, {}

        field_meta_map = {f.name: f for f in meta.fields}
        link_titles: dict[str, str] = {}

        for field_name in fields:
            fm = field_meta_map.get(field_name)
            if not fm:
                continue

            fk_value = data.get(field_name)
            if not fk_value:
                continue

            link_entity_name: Optional[str] = None

            if fm.field_type == "link" and fm.link_entity:
                link_entity_name = fm.link_entity
            elif fm.field_type == "query_link" and fm.query:
                query_key = (
                    fm.query.get("key")
                    if isinstance(fm.query, dict)
                    else getattr(fm.query, "key", None)
                )
                if query_key:
                    try:
                        from app.application.services.documents.query_link import QUERY_LINK_TARGET_ENTITY

                        link_entity_name = QUERY_LINK_TARGET_ENTITY.get(query_key)
                    except Exception:
                        link_entity_name = None
            elif fm.field_type == "parent_child_link" and fm.child_entity:
                link_entity_name = fm.child_entity

            if not link_entity_name:
                continue

            linked_meta = MetaRegistry.get(link_entity_name)
            if not linked_meta:
                continue

            title_field = linked_meta.title_field or "id"
            title = await self.repo.get_title(link_entity_name, str(fk_value), title_field)
            if title:
                link_titles[f"{link_entity_name}::{fk_value}"] = title

        return data, link_titles
