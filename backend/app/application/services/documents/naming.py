from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.framework.models.infrastructure import Series
from app.meta.registry import NamingMeta


class NamingService:
    """
    Naming service for generating human-readable IDs.
    
    IDs follow the pattern: PREFIX-{####}
    Examples: AST-0001, WO-0001, TODO-0001
    
    The ID IS the primary key - no separate UUID.
    """
    
    @staticmethod
    async def generate_id(db: AsyncSession, naming: NamingMeta, entity: str | None = None) -> str:
        """
        Generate a new ID based on the naming configuration.
        
        This ID becomes the primary key of the record.
        
        Args:
            db: Database session
            naming: Naming configuration from entity metadata
            
        Returns:
            Generated ID (e.g., "AST-0001") or None if naming disabled
        """
        if not naming or not naming.enabled:
            return None

        if entity:
            from app.application.services.documents.document_query import _get_model

            model = _get_model(entity)
            if model is not None:
                prefix_like = f"{naming.prefix}-%"
                result = await db.execute(
                    select(model.id)
                    .where(model.id.like(prefix_like))
                    .order_by(model.id.desc())
                    .limit(1)
                )
                latest_id = result.scalar_one_or_none()
            else:
                latest_id = None
        else:
            latest_id = None

        existing_current = 0
        if latest_id:
            try:
                existing_current = int(str(latest_id).split("-")[-1])
            except (TypeError, ValueError):
                existing_current = 0
        
        # Get or create series for this prefix
        result = await db.execute(select(Series).where(Series.name == naming.prefix))
        series = result.scalar_one_or_none()
        
        if not series:
            series = Series(name=naming.prefix, current=existing_current)
            db.add(series)
        elif existing_current > (series.current or 0):
            series.current = existing_current
        
        # Increment sequence
        series.current += 1
        await db.flush()  # Ensure update happens in transaction
        
        # Format ID: PREFIX-0001
        generated_id = f"{naming.prefix}-{str(series.current).zfill(naming.digits)}"
        return generated_id
    
    @staticmethod
    async def generate_code(db: AsyncSession, naming: NamingMeta) -> str:
        """
        Alias for generate_id for backward compatibility.
        
        Deprecated: Use generate_id instead.
        """
        return await NamingService.generate_id(db, naming)
    
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
