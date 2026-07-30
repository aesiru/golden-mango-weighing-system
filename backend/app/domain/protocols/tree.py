"""
Tree-related domain protocols.
"""
from typing import Protocol, List, Dict, Any, Optional
from abc import abstractmethod


class TreeRepositoryProtocol(Protocol):
    """Protocol for tree data operations."""
    
    @abstractmethod
    async def get_tree_data(
        self, 
        entity_name: str, 
        parent_field: Optional[str] = None,
        title_field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all records for tree structure with minimal fields."""
        pass
