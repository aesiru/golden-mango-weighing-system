"""
API Layer
==========
FastAPI routes — thin handlers that delegate to application services.
"""
from .router import api_router

__all__ = ["api_router"]
