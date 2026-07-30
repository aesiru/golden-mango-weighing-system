"""
Exceptions Module
=================
Custom exceptions and error handling for the API.

Exception Classes:
- APIException: Base exception class
- NotFoundError: 404 - Resource not found
- BadRequestError: 400 - Invalid request
- UnauthorizedError: 401 - Authentication required
- ForbiddenError: 403 - Permission denied
- ConflictError: 409 - Duplicate entry
- InternalServerError: 500 - Server error

All exceptions return consistent JSON format:
{
    "status": "error",
    "message": "Human-readable message",
    "details": { ... },
    "code": <http_status_code>
}

Last Updated: 2026-01-29
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.application.services.integrations.error_logger import log_error


def _should_log_error(status_code: int | None) -> bool:
    """System-level logging only for security/database/internal errors."""
    if status_code is None:
        return False
    return status_code >= 500 or status_code in {401, 403, 409}


class APIException(Exception):
    """Base API exception."""
    def __init__(self, status_code: int, message: str, details: dict = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(APIException):
    """Resource not found (404)."""
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(status.HTTP_404_NOT_FOUND, message, {"resource": resource, "identifier": identifier})


class BadRequestError(APIException):
    """Bad request (400)."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(status.HTTP_400_BAD_REQUEST, message, details)


class UnauthorizedError(APIException):
    """Unauthorized (401)."""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, message)


class ForbiddenError(APIException):
    """Forbidden (403)."""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(status.HTTP_403_FORBIDDEN, message)


class ConflictError(APIException):
    """Conflict (409) - e.g., duplicate entry."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(status.HTTP_409_CONFLICT, message, details)


class InternalServerError(APIException):
    """Internal server error (500)."""
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, message)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    if _should_log_error(exc.status_code):
        await log_error(exc.status_code, exc.__class__.__name__, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "details": exc.details,
            "code": exc.status_code,
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with clear messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    if _should_log_error(status.HTTP_422_UNPROCESSABLE_ENTITY):
        await log_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "ValidationError", str(errors))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "details": {"errors": errors},
            "code": 422,
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    if isinstance(exc, IntegrityError):
        # Parse integrity error for better message
        error_str = str(exc.orig) if exc.orig else str(exc)
        error_lower = error_str.lower()
        
        if "unique constraint" in error_lower or "unique constraint failed" in error_lower or "duplicate key" in error_lower:
            if _should_log_error(status.HTTP_409_CONFLICT):
                await log_error(status.HTTP_409_CONFLICT, "IntegrityError", error_str)
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status": "error",
                    "message": "A record with this value already exists",
                    "details": {"type": "duplicate_entry", "error": error_str},
                    "code": 409,
                }
            )
        
        if "foreign key constraint" in error_lower or "foreign key" in error_lower:
            if _should_log_error(status.HTTP_400_BAD_REQUEST):
                if _should_log_error(status.HTTP_400_BAD_REQUEST):
                    await log_error(status.HTTP_400_BAD_REQUEST, "NotNullViolation", error_str)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "Referenced record does not exist",
                    "details": {"type": "foreign_key_violation", "error": error_str},
                    "code": 400,
                }
            )

        if "not null constraint" in error_lower or "null value" in error_lower:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "A required database field was null",
                    "details": {"type": "not_null_violation", "error": error_str},
                    "code": 400,
                },
            )

        if "check constraint" in error_lower:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "A database constraint was violated",
                    "details": {"type": "check_constraint_violation", "error": error_str},
                    "code": 400,
                },
            )

    # Generic database error
    try:
        error_str = str(getattr(exc, "orig", None) or exc)
    except Exception:
        error_str = ""
    if _should_log_error(status.HTTP_500_INTERNAL_SERVER_ERROR):
        await log_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "DatabaseError", error_str)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Database error occurred",
            "details": {"type": "database_error", "error": error_str},
            "code": 500,
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    import traceback
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    if _should_log_error(status.HTTP_500_INTERNAL_SERVER_ERROR):
        await log_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc.__class__.__name__, traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "details": {"type": "internal_error"},
            "code": 500,
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import SQLAlchemyError
    
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
