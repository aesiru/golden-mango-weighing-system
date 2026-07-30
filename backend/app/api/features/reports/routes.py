"""Reports Router
===============
Legacy reporting endpoints have been disabled for the core framework.
"""
from fastapi import APIRouter

router = APIRouter(tags=["reports"])
