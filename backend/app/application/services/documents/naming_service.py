"""
Naming Service (Application Layer)
==================================
CLEAN architecture-compliant naming service.

Orchestrates ID generation using NamingRepository.
Delegates data access to infrastructure layer.
"""
from typing import Optional

from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.meta.registry import NamingMeta


class NamingAppService:
    """
    Application-layer naming orchestration.
    
    Generates human-readable IDs (e.g., AST-0001, WO-0001).
    """

    def __init__(self, naming_repo: NamingRepository):
        self._naming_repo = naming_repo

    async def generate_id(self, naming: NamingMeta, entity: str | None = None) -> Optional[str]:
        """
        Generate a new ID based on the naming configuration.
        
        This ID becomes the primary key of the record.
        
        Args:
            naming: Naming configuration from entity metadata
            entity: Entity name to check for existing IDs
            
        Returns:
            Generated ID (e.g., "AST-0001") or None if naming disabled
        """
        if not naming or not naming.enabled:
            return None

        existing_current = 0
        if entity:
            latest_id = await self._naming_repo.get_latest_id_for_prefix(entity, naming.prefix)
            if latest_id:
                try:
                    existing_current = int(str(latest_id).split("-")[-1])
                except (TypeError, ValueError):
                    existing_current = 0

        # Update series if current value is higher than stored
        current_value = await self._naming_repo.get_current_value(naming.prefix)
        if current_value is None:
            current_value = 0
        if existing_current > current_value:
            # Sync the series counter so get_next_id starts from the right value.
            await self._naming_repo.set_current_value(naming.prefix, existing_current)

        # Generate the next ID
        return await self._naming_repo.get_next_id(naming.prefix, naming.digits)

    @staticmethod
    def parse_naming_format(naming_str: str) -> tuple[str, int]:
        """
        Parse naming format string to extract prefix and digit count.
        
        Args:
            naming_str: Format like "AST-{####}" or "WO-{######}"
            
        Returns:
            Tuple of (prefix, digit_count)
        """
        if not naming_str or "{" not in naming_str:
            return None, 0
        
        parts = naming_str.split("-{")
        if len(parts) != 2:
            return None, 0
        
        prefix = parts[0]
        digit_part = parts[1].rstrip("}")
        digit_count = len(digit_part)
        
        return prefix, digit_count
