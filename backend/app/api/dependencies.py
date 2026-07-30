"""
API Dependencies
=================
FastAPI Depends() factories for injecting application services.
Wires infrastructure implementations to application-layer services.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token

# Infrastructure
from app.infrastructure.database.repositories.entity_repository import EntityRepository
from app.infrastructure.database.repositories.auth_repository import AuthRepository
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.infrastructure.database.repositories.fetch_from_repository import FetchFromRepository
from app.infrastructure.database.repositories.notification_subscription_repository import NotificationSubscriptionRepository
from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.auth.jwt_service import JWTService
from app.infrastructure.auth.password_service import PasswordService
from app.application.services.notifications.socketio import socket_manager

# Application services
from app.application.services.entity_service import EntityService
from app.application.services.auth.auth_service import AuthService
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.workflows.workflow_service import WorkflowAppService
from app.application.services.workflows.workflow_progress_service import WorkflowProgressService
from app.application.services.dashboards.dashboard_service import DashboardAppService
from app.application.services.fetch_from_service import FetchFromService
from app.application.services.documents.naming_service import NamingAppService
from app.application.services.documents.document_service import DocumentAppService
from app.application.services.notifications.notification_subscription_service import NotificationSubscriptionService
from app.application.services.notifications.email_notification_service import EmailNotificationService
from app.application.email_notifications.dispatcher import EmailNotificationDispatcher


# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------

def get_entity_repo(db: AsyncSession = Depends(get_db)) -> EntityRepository:
    return EntityRepository(db)


def get_auth_repo(db: AsyncSession = Depends(get_db)) -> AuthRepository:
    return AuthRepository(db)


def get_workflow_repo(db: AsyncSession = Depends(get_db)) -> WorkflowRepository:
    return WorkflowRepository(db)


def get_naming_repo(db: AsyncSession = Depends(get_db)) -> NamingRepository:
    return NamingRepository(db)


def get_fetch_from_repo(db: AsyncSession = Depends(get_db)) -> FetchFromRepository:
    return FetchFromRepository(db)


def get_notification_subscription_repo(
    db: AsyncSession = Depends(get_db),
) -> NotificationSubscriptionRepository:
    return NotificationSubscriptionRepository(db)


def get_dashboard_repo(db: AsyncSession = Depends(get_db)) -> DashboardRepository:
    return DashboardRepository(db)


def get_document_repo(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_naming_repo(db: AsyncSession = Depends(get_db)) -> NamingRepository:
    return NamingRepository(db)


# ---------------------------------------------------------------------------
# Infrastructure service singletons
# ---------------------------------------------------------------------------

_jwt_service = JWTService()
_password_service = PasswordService()


def get_jwt_service() -> JWTService:
    return _jwt_service


def get_password_service() -> PasswordService:
    return _password_service


# ---------------------------------------------------------------------------
# Application service factories
# ---------------------------------------------------------------------------

def get_entity_service(
    entity_repo: EntityRepository = Depends(get_entity_repo),
    naming_repo: NamingRepository = Depends(get_naming_repo),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    auth_repo: AuthRepository = Depends(get_auth_repo),
) -> EntityService:
    rbac = RBACAppService(auth_repo)
    return EntityService(
        entity_repo=entity_repo,
        naming_repo=naming_repo,
        rbac_service=rbac,
        workflow_repo=workflow_repo,
        socket_manager=socket_manager,
    )


def get_auth_service(
    auth_repo: AuthRepository = Depends(get_auth_repo),
) -> AuthService:
    return AuthService(
        auth_repo=auth_repo,
        jwt_service=_jwt_service,
        password_service=_password_service,
    )


def get_rbac_service(
    auth_repo: AuthRepository = Depends(get_auth_repo),
) -> RBACAppService:
    return RBACAppService(auth_repo)


def get_workflow_service(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> WorkflowAppService:
    return WorkflowAppService(workflow_repo=workflow_repo, entity_repo=entity_repo)


def get_workflow_progress_service(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    entity_repo: EntityRepository = Depends(get_entity_repo),
) -> WorkflowProgressService:
    return WorkflowProgressService(workflow_repo=workflow_repo, entity_repo=entity_repo)


def get_dashboard_service(
    dashboard_repo: DashboardRepository = Depends(get_dashboard_repo),
) -> DashboardAppService:
    return DashboardAppService(dashboard_repo, current_user=None, start_date=None, end_date=None)


def get_naming_service(
    naming_repo: NamingRepository = Depends(get_naming_repo),
) -> NamingAppService:
    return NamingAppService(naming_repo)


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> DocumentAppService:
    return DocumentAppService(document_repo)


def get_fetch_from_service(
    repo: FetchFromRepository = Depends(get_fetch_from_repo),
) -> FetchFromService:
    return FetchFromService(repo)


def get_notification_subscription_service(
    repo: NotificationSubscriptionRepository = Depends(get_notification_subscription_repo),
) -> NotificationSubscriptionService:
    return NotificationSubscriptionService(repo)


# ---------------------------------------------------------------------------
# Email Notification service factory
# ---------------------------------------------------------------------------

def build_email_notification_service(
    notification_subscription_service: NotificationSubscriptionService,
) -> EmailNotificationService:
    """Construct EmailNotificationService (usable from tests without FastAPI Depends)."""
    from app.infrastructure.email.smtp_service import SmtpEmailService
    from app.infrastructure.email.template_renderer import JinjaEmailTemplateRenderer

    return EmailNotificationService(
        email_service=SmtpEmailService(),
        template_renderer=JinjaEmailTemplateRenderer(),
        notification_subscription_service=notification_subscription_service,
    )


def get_email_notification_service(
    notification_subscription_service: NotificationSubscriptionService = Depends(get_notification_subscription_service),
):
    """Factory for EmailNotificationService with infrastructure wired."""
    return build_email_notification_service(notification_subscription_service)


def get_email_notification_dispatcher(
    email_notification_service=Depends(get_email_notification_service),
) -> EmailNotificationDispatcher:
    return EmailNotificationDispatcher(email_notification_service)


# ---------------------------------------------------------------------------
# Import/Export service factory
# ---------------------------------------------------------------------------

def get_import_export_service(db: AsyncSession = Depends(get_db)):
    """Factory for ImportExportService."""
    from app.application.services.import_export_service import ImportExportService
    return ImportExportService(db)


# ---------------------------------------------------------------------------
# Scheduler service factory
# ---------------------------------------------------------------------------

def get_scheduler_adapter():
    """Factory for SchedulerAdapter (infrastructure)."""
    from app.infrastructure.scheduler.scheduler_adapter import SchedulerAdapter
    return SchedulerAdapter()


def get_scheduler_service(scheduler_adapter = Depends(get_scheduler_adapter)):
    """Factory for SchedulerAppService."""
    from app.application.services.scheduling.scheduler import SchedulerAppService
    return SchedulerAppService(scheduler_adapter)


# ---------------------------------------------------------------------------
# Metadata Sync service factory
# ---------------------------------------------------------------------------

def get_metadata_sync_service():
    """Factory for MetadataSyncService with all infrastructure adapters wired."""
    from app.infrastructure.metadata.adapters import (
        JsonMetadataReader,
        JsonMetadataWriter,
        MetadataValidator,
        MetadataChangeAnalyzer,
        ModelGeneratorAdapter,
        MigrationManagerAdapter,
        RegistryManagerAdapter,
    )
    from app.application.services.integrations.metadata_sync_service import MetadataSyncService

    reader = JsonMetadataReader()
    return MetadataSyncService(
        reader=reader,
        writer=JsonMetadataWriter(reader),
        validator=MetadataValidator(),
        analyzer=MetadataChangeAnalyzer(reader),
        model_generator=ModelGeneratorAdapter(),
        migration_manager=MigrationManagerAdapter(),
        registry_manager=RegistryManagerAdapter(),
    )


# ---------------------------------------------------------------------------
# Legacy service factories (for gradual migration of routes to Depends())
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Centralised entity RBAC dependency
# ---------------------------------------------------------------------------

def require_entity_permission(action: str):
    """
    Return a FastAPI ``Depends``-compatible callable that enforces entity-level
    RBAC before the route handler is invoked.

    Usage::

        @router.get("/{entity}/list", dependencies=[Depends(require_entity_permission("read"))])
        async def get_list(entity: str, ...):
            ...

    The dependency resolves ``entity`` from the path, the current user from the
    JWT token, and delegates to ``RBACAppService.check_permission``.  Superusers
    bypass all checks.  Raises ``ForbiddenError`` (HTTP 403) on denial.
    """
    from typing import Optional as _Optional
    from fastapi import Header as _Header
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
    from app.core.database import get_db as _get_db
    from app.core.security import get_current_user_from_token as _get_user
    from app.core.exceptions import ForbiddenError as _ForbiddenError
    from app.meta.registry import MetaRegistry as _MetaRegistry

    async def _check(
        entity: str,
        authorization: _Optional[str] = _Header(None),
        db: _AsyncSession = Depends(_get_db),
        rbac: RBACAppService = Depends(get_rbac_service),
    ) -> None:
        user = await _get_user(authorization, db)
        if user.is_superuser:
            return
        allowed = await rbac.check_permission(
            user_id=user.id,
            entity=entity,
            action=action,
            role_ids=user.role_ids,
            is_superuser=user.is_superuser,
        )
        if not allowed:
            meta = _MetaRegistry.get(entity)
            label = meta.label if meta else entity.replace("_", " ").title()
            raise _ForbiddenError(f"You don't have permission to {action} {label}")

    return _check

