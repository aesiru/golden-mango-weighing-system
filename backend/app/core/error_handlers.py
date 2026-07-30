"""
Core Layer: Error Handling

Decorator and utilities for consistent API error responses.

Clean Architecture Layer: Core
Responsibility: Provide error handling utilities for API responses
"""
from functools import wraps
from typing import Callable, Any
import traceback
import logging
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.schemas.base import ActionResponse

logger = logging.getLogger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator to handle common API errors and return consistent error responses.
    
    Usage:
        @router.get("/endpoint")
        @handle_api_errors
        async def my_endpoint(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except IntegrityError as e:
            logger.error(f"Database integrity error in {func.__name__}: {str(e)}")
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if "foreign key constraint" in error_msg.lower():
                return ActionResponse(
                    status="error",
                    message="Cannot complete operation due to related records",
                    errors={"database": "Foreign key constraint violation"}
                )
            elif "unique constraint" in error_msg.lower():
                return ActionResponse(
                    status="error",
                    message="A record with this value already exists",
                    errors={"database": "Unique constraint violation"}
                )
            else:
                return ActionResponse(
                    status="error",
                    message="Database constraint violation",
                    errors={"database": error_msg}
                )
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
            return ActionResponse(
                status="error",
                message="Database operation failed",
                errors={"database": str(e)}
            )
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return ActionResponse(
                status="error",
                message="Invalid input value",
                errors={"validation": str(e)}
            )
        except KeyError as e:
            logger.warning(f"Missing key in {func.__name__}: {str(e)}")
            return ActionResponse(
                status="error",
                message=f"Missing required field: {str(e)}",
                errors={"missing_field": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
            return ActionResponse(
                status="error",
                message="An unexpected error occurred",
                errors={"error": str(e), "type": type(e).__name__}
            )
    
    return wrapper


def safe_dict_response(status: str, message: str, data: Any = None, errors: dict = None) -> dict:
    """
    Create a safe dictionary response with consistent structure.
    
    Args:
        status: "success" or "error"
        message: Human-readable message
        data: Optional data payload
        errors: Optional error details
    
    Returns:
        Dictionary with consistent response structure
    """
    response = {
        "status": status,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    if errors is not None:
        response["errors"] = errors
    
    return response
