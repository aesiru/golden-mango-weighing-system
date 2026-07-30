"""
Domain Exceptions
==================
Pure business exceptions — no HTTP or framework dependencies.
These are caught and translated to HTTP responses by the API layer.
"""


class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(DomainException):
    """Raised when an entity or record is not found."""
    def __init__(self, entity: str, identifier: str = None):
        message = f"{entity} not found"
        if identifier:
            message = f"{entity} '{identifier}' not found"
        super().__init__(message, {"entity": entity, "identifier": identifier})


class ValidationError(DomainException):
    """Raised when business validation fails."""
    def __init__(self, message: str, field_errors: dict = None):
        super().__init__(message, {"field_errors": field_errors or {}})
        self.field_errors = field_errors or {}


class PermissionDeniedError(DomainException):
    """Raised when a user lacks permission for an action."""
    def __init__(self, message: str = "Permission denied", entity: str = None, action: str = None):
        super().__init__(message, {"entity": entity, "action": action})


class DuplicateRecordError(DomainException):
    """Raised when a duplicate record is detected."""
    def __init__(self, message: str = "A record with this value already exists", details: dict = None):
        super().__init__(message, details)


class WorkflowError(DomainException):
    """Raised when a workflow transition is invalid."""
    def __init__(self, message: str, current_state: str = None, action: str = None):
        super().__init__(message, {"current_state": current_state, "action": action})
