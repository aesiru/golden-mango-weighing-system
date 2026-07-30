"""
Entity tree endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional

from app.application.services.tree_service import TreeService
from app.infrastructure.database.repositories.tree import TreeRepository
from app.api.dependencies import get_db, require_entity_permission
from app.domain.exceptions import EntityNotFoundError

router = APIRouter(tags=["tree"])


def get_tree_service(db_session=Depends(get_db)) -> TreeService:
    """Dependency injection for tree service."""
    tree_repository = TreeRepository(db_session)
    return TreeService(tree_repository)


@router.get("/{entity}/tree", dependencies=[Depends(require_entity_permission("read"))])
async def get_entity_tree(
    entity: str,
    parent_field: Optional[str] = Query(None, description="Override parent field"),
    title_field: Optional[str] = Query(None, description="Override title field"),
    tree_service: TreeService = Depends(get_tree_service)
) -> Dict[str, Any]:
    """Get tree data for an entity."""
    
    try:
        data = await tree_service.get_tree_data(
            entity_name=entity,
            parent_field=parent_field,
            title_field=title_field
        )
        
        return {
            "status": "success",
            "data": data,
            "count": len(data)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
