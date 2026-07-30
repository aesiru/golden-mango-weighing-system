"""
Common utilities for admin routers.
"""
import re
from typing import Any


def api_response(status: str, message: str, data: Any = None) -> dict:
    """Create a standardized API response."""
    response = {"status": status, "message": message}
    if data is not None:
        response["data"] = data
    return response


def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None
