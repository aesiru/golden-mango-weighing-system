"""
Core Layer: Seed Facade

Entry point for running all database seeders.

Clean Architecture Layer: Core
Responsibility: Provide seed data initialization entry point
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.seeds import run_all_seeds


async def run_seeds(db: AsyncSession) -> None:
    """Run all seed functions. Called by the app lifespan on startup."""
    await run_all_seeds(db)


async def seed_data() -> None:
    """Entry point for the forge CLI seed command."""
    from app.core.database import async_session_maker
    async with async_session_maker() as db:
        await run_seeds(db)
