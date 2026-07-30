"""Stock Count feature stub.
============================
Legacy stock count APIs have been disabled for the core framework.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/stock-count", tags=["stock-count"])
