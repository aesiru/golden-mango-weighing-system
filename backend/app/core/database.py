"""
Core Layer: Database Setup

SQLAlchemy async engine, session factory, and Base model.

Clean Architecture Layer: Core
Responsibility: Provide database connection and ORM configuration
"""
import time
import logging

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

slow_query_logger = logging.getLogger("slow_queries")

_is_sqlite = "sqlite" in settings.DATABASE_URL

_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    }
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    **_pool_kwargs,
)

# ---------------------------------------------------------------------------
# Slow-query event listeners (logs any query taking >100ms) - DISABLED
# ---------------------------------------------------------------------------
# @event.listens_for(engine.sync_engine, "before_cursor_execute")
# def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     conn.info.setdefault("query_start_time", []).append(time.time())

# @event.listens_for(engine.sync_engine, "after_cursor_execute")
# def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     total = time.time() - conn.info["query_start_time"].pop(-1)
#     if total > 0.1:  # 100ms threshold
#         slow_query_logger.warning(
#             "SLOW QUERY (%dms):\n%s\nParams: %s", int(total * 1000), statement, parameters
#         )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
