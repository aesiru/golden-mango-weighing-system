"""
Dashboard Repository
====================
Minimal dashboard repository stub for the core framework.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardRepository:
    """Concrete dashboard repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db
