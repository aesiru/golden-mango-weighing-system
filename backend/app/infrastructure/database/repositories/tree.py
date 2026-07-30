"""
Tree repository implementation.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.domain.protocols.tree import TreeRepositoryProtocol
from app.meta.registry import MetaRegistry


class TreeRepository(TreeRepositoryProtocol):
    """SQLAlchemy implementation of tree repository."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tree_data(
        self, 
        entity_name: str, 
        parent_field: Optional[str] = None,
        title_field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all records for tree structure with minimal fields."""
        
        # Get entity metadata
        entity_meta = MetaRegistry.get(entity_name)
        if not entity_meta:
            raise ValueError(f"Entity {entity_name} not found")
        
        # Determine fields to select
        fields_to_select = ["id"]
        
        # Add parent field
        if parent_field:
            fields_to_select.append(parent_field)
        elif entity_meta.tree_parent_field:
            fields_to_select.append(entity_meta.tree_parent_field)
        else:
            # Try to find a parent field heuristically
            for field_name, field_meta in entity_meta.fields.items():
                if field_meta.field_type == "Link" and field_meta.options == entity_name:
                    fields_to_select.append(field_name)
                    break
        
        # Add title field
        if title_field:
            fields_to_select.append(title_field)
        elif entity_meta.title_field:
            fields_to_select.append(entity_meta.title_field)
        else:
            fields_to_select.append("name")  # Default fallback
        
        # Build and execute query
        table_name = entity_name
        select_clause = ", ".join(fields_to_select)
        
        query = text(f"""
            SELECT {select_clause}
            FROM {table_name}
            ORDER BY {fields_to_select[-1]}  -- Order by title field
        """)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        # Convert to list of dicts
        data = []
        for row in rows:
            row_dict = {}
            for i, field in enumerate(fields_to_select):
                row_dict[field] = row[i]
            data.append(row_dict)
        
        return data
