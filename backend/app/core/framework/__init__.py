"""
Core Framework - Public API
===========================

Auto-available foundation entities for all modules.

This module provides centralized access to all core framework entities,
schemas, and utilities. Import from here for guaranteed stability.

Examples:
    >>> from app.core.framework import User, Role, EntityPermission
    >>> from app.core.framework import ErrorLog, AuditLog, Attachment
    >>> from app.core.framework.schemas import UserCreate, RoleUpdate

Note:
    Core entities require DEVELOPER_MODE=1 to edit via Model Editor.
    This protects system integrity from accidental modifications.
"""
from typing import TYPE_CHECKING

# =============================================================================
# VERSION & METADATA
# =============================================================================

__version__ = "1.0.0"
__all__ = [
    # Core Framework Version
    "__version__",
    # Initialization
    "initialize_core_framework",
    "is_initialized",
    # Entity Access
    "get_core_entity",
    "list_core_entities",
    # Auth Entities
    "User",
    "Role",
    "EntityPermission",
    "user_roles",
    # Infrastructure Entities
    "ErrorLog",
    "AuditLog",
    "Attachment",
    "EmailLog",
    "NotificationSubscription",
    "ScheduledJobLog",
    "UserActivity",
    "Series",
    # Ordering Entities
    "ModuleOrder",
    "EntityOrder",
    # Workflow Entities
    "WorkflowState",
    "WorkflowAction",
    "Workflow",
    "WorkflowStateLink",
    "WorkflowTransition",
    "generate_slug",
]

# =============================================================================
# LAZY INITIALIZATION
# =============================================================================

_framework_initialized: bool = False


def initialize_core_framework() -> None:
    """Initialize core framework entities and contracts.
    
    Called automatically on first import. Idempotent - safe to call multiple times.
    
    This function:
    1. Registers core models with entity repository
    2. Validates entity metadata consistency
    3. Sets up framework contracts
    
    Modules should NOT call this directly - it's handled automatically.
    """
    global _framework_initialized
    
    if _framework_initialized:
        return
    
    from app.core.framework.contracts import (
        EntityContract,
        InitializationContract,
        InitializationPhase,
        ModuleContract,
    )
    from app.infrastructure.database.repositories.entity_repository import register_core_models

    InitializationContract.set_phase(InitializationPhase.LOADING_ENTITIES)
    core_entities = _register_core_entities()

    InitializationContract.set_phase(InitializationPhase.REGISTERING_MODELS)
    register_core_models()
    EntityContract.register_core_models(_build_core_model_registry())

    InitializationContract.set_phase(InitializationPhase.SETUP_CONTRACTS)
    ModuleContract.register_framework_contracts(list(core_entities.keys()))
    InitializationContract.set_initialized()
    _framework_initialized = True


def is_initialized() -> bool:
    """Check if core framework has been initialized."""
    return _framework_initialized


def _register_core_entities() -> dict[str, object]:
    """Register all core entities with the framework contracts."""
    from app.core.framework.contracts import EntityContract
    from app.core.framework.entities import iter_entity_paths
    from app.entities import load_entity_from_json

    core_entities = {}
    for entity_path in iter_entity_paths():
        entity_meta = load_entity_from_json(entity_path, module_name="core")
        if entity_meta is None:
            continue
        if not EntityContract.validate_entity_metadata(entity_meta):
            raise ValueError(f"Invalid core entity metadata: {entity_path.name}")
        core_entities[entity_meta.name] = entity_meta

    EntityContract.register_core_entities(core_entities)
    return core_entities


def _build_core_model_registry() -> dict[str, object]:
    """Build the canonical core entity to model mapping."""
    return {
        "user": User,
        "role": Role,
        "entity_permission": EntityPermission,
        "error_log": ErrorLog,
        "audit_log": AuditLog,
        "attachment": Attachment,
        "email_log": EmailLog,
        "notification_subscription": NotificationSubscription,
        "scheduled_job_log": ScheduledJobLog,
        "user_activity": UserActivity,
        "series": Series,
        "module_order": ModuleOrder,
        "entity_order": EntityOrder,
        "workflow_state": WorkflowState,
        "workflow_action": WorkflowAction,
        "workflow": Workflow,
        "workflow_state_link": WorkflowStateLink,
        "workflow_transition": WorkflowTransition,
    }


# =============================================================================
# ENTITY ACCESS FUNCTIONS
# =============================================================================

def get_core_entity(entity_name: str):
    """Get a core entity class by name.
    
    Args:
        entity_name: Name of the entity (e.g., 'user', 'role', 'error_log')
        
    Returns:
        SQLAlchemy model class for the entity
        
    Raises:
        KeyError: If entity not found
        
    Example:
        >>> User = get_core_entity('user')
        >>> user = User(username='john', email='john@example.com')
    """
    from app.core.framework.contracts import EntityContract
    from app.infrastructure.database.repositories.entity_repository import get_entity_model
    
    # Ensure initialized
    if not _framework_initialized:
        initialize_core_framework()
    
    entity = EntityContract.get_core_model(entity_name) or get_entity_model(entity_name)
    if entity is None:
        raise KeyError(f"Core entity '{entity_name}' not found. "
                      f"Available: {', '.join(list_core_entities())}")
    return entity


def list_core_entities():
    """List all available core entity names.
    
    Returns:
        List of entity name strings
        
    Example:
        >>> entities = list_core_entities()
        >>> print(entities)
        ['user', 'role', 'entity_permission', 'error_log', 'audit_log', 'attachment']
    """
    # Ensure initialized
    if not _framework_initialized:
        initialize_core_framework()
    
    from app.core.framework.contracts import EntityContract

    return EntityContract.list_core_entities()


# ==============================================================================
# AUTH ENTITIES (Authentication & Authorization)
# ==============================================================================

# Import models (lazy to avoid circular imports)
from app.core.framework.models.auth import (
    User,
    Role,
    EntityPermission,
    user_roles,
)

# ==============================================================================
# INFRASTRUCTURE ENTITIES (System Logging & Storage)
# ==============================================================================

from app.core.framework.models.infrastructure import (
    ErrorLog,
    AuditLog,
    Attachment,
    EmailLog,
    NotificationSubscription,
    ScheduledJobLog,
    UserActivity,
    Series,
)

# ==============================================================================
# ORDERING ENTITIES (Module & Entity Display Order)
# ==============================================================================

from app.core.framework.models.ordering import (
    ModuleOrder,
    EntityOrder,
)

# ==============================================================================
# WORKFLOW ENTITIES (State Machine & Workflow Engine)
# ==============================================================================

from app.core.framework.models.workflow import (
    WorkflowState,
    WorkflowAction,
    Workflow,
    WorkflowStateLink,
    WorkflowTransition,
    generate_slug,
)

# =============================================================================
# AUTO-INITIALIZE ON IMPORT
# =============================================================================

# Initialize on first import - safe and idempotent
initialize_core_framework()
