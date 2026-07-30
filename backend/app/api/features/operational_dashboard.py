"""Operational Dashboard stub.
=============================
Legacy dashboard endpoints have been disabled for the core framework.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/operations/dashboard", tags=["operations"])
