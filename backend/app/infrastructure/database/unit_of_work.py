"""
SQLAlchemy Unit of Work
=======================
Concrete implementation of UnitOfWorkProtocol using SQLAlchemy async sessions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker


class SQLAlchemyUnitOfWork:
    """Manages a database transaction as a unit of work."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or async_session_maker
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> 'SQLAlchemyUnitOfWork':
        self.session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        if self.session:
            await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()
