"""
Database Connection
====================
SQLAlchemy engine, session factory, and Base.
Re-exported from app.core.database for backward compatibility.
"""
from app.core.database import (
    engine,
    async_session_maker,
    Base,
    get_db,
    init_db,
)

__all__ = ["engine", "async_session_maker", "Base", "get_db", "init_db"]
