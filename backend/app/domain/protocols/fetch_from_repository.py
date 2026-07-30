from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class FetchFromRepositoryProtocol(Protocol):
    async def get_partial_fields(
        self,
        entity: str,
        record_id: str,
        fields: list[str],
    ) -> Optional[dict[str, Any]]:
        ...

    async def get_title(
        self,
        entity: str,
        record_id: str,
        title_field: str,
    ) -> Optional[str]:
        ...
