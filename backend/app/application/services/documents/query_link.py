"""
Query Link Handlers
===================
Whitelisted query methods for query_link field type.
Each key maps to a specific handler function that returns options.
"""
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def sample_test_query(
    db: AsyncSession,
    entity: str,
    field: str,
    form_state: Optional[dict] = None,
    static_params: Optional[dict] = None
) -> list[dict]:
    """
    Sample test query handler that returns a simple test option.
    Used for testing query_link field type.
    """
    return [
        {
            "value": "hello",
            "label": "hello"
        }
    ]


async def request_activity_type_query(
    db: AsyncSession,
    entity: str,
    field: str,
    form_state: Optional[dict] = None,
    static_params: Optional[dict] = None
) -> list[dict]:
    """
    Query link support for request activity type has been disabled
    after the asset/maintenance modules were removed.
    """
    return []


# Whitelist mapping: key -> handler function
QUERY_HANDLERS = {
    "sample_test": sample_test_query,
    "request_activity_type": request_activity_type_query,
}


# Whitelist mapping: key -> handler function
QUERY_HANDLERS = {
    "sample_test": sample_test_query,
    "request_activity_type": request_activity_type_query,
}


QUERY_LINK_TARGET_ENTITY: dict[str, str] = {
    "request_activity_type": "request_activity_type",
}


async def execute_query_link(
    key: str,
    db: AsyncSession,
    entity: str,
    field: str,
    form_state: Optional[dict] = None,
    static_params: Optional[dict] = None
) -> dict:
    """
    Execute a whitelisted query link handler.
    
    Args:
        key: Whitelisted handler key
        db: Database session
        entity: Entity name
        field: Field name
        form_state: Current form data
        static_params: Static parameters from field config
        
    Returns:
        Dict with status and options list
    """
    handler = QUERY_HANDLERS.get(key)
    
    if not handler:
        return {
            "status": "error",
            "message": f"Unknown query key: {key}",
            "options": []
        }
    
    try:
        options = await handler(
            db=db,
            entity=entity,
            field=field,
            form_state=form_state,
            static_params=static_params
        )
        
        return {
            "status": "success",
            "options": options
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Query execution failed: {str(e)}",
            "options": []
        }
