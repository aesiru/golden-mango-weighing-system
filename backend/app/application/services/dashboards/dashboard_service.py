"""
Dashboard Service (Application Layer)
=====================================
Minimal dashboard service stub for the core framework.
"""
from typing import Any, Optional

from app.core.security import CurrentUser
from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository

DASHBOARD_DEFINITIONS: dict[str, dict[str, Any]] = {}
WIDGET_DASHBOARD_MAP: dict[str, str] = {}
DASHBOARD_ORDER: list[str] = []
ROLE_WIDGET_MAP: dict[str, list[dict[str, Any]]] = {}
SUPERUSER_WIDGETS: list[dict[str, Any]] = []
WIDGET_TITLES: dict[str, str] = {}


class DashboardAppService:
    """Minimal dashboard orchestration for the core framework."""

    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        current_user: CurrentUser,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        self._dashboard_repo = dashboard_repo
        self.current_user = current_user
        self.start_date = start_date
        self.end_date = end_date

    def _resolve_user_widgets(self) -> list[dict[str, Any]]:
        if self.current_user and self.current_user.is_superuser:
            return SUPERUSER_WIDGETS

        user_roles = self.current_user.roles or []
        seen_types: set[str] = set()
        merged: list[dict[str, Any]] = []

        for role in user_roles:
            for widget_cfg in ROLE_WIDGET_MAP.get(role, []):
                w_type = widget_cfg["type"]
                if w_type not in seen_types:
                    seen_types.add(w_type)
                    merged.append(widget_cfg)

        return merged

    def resolve_user_widgets(self) -> list[dict[str, Any]]:
        return self._resolve_user_widgets()

    async def fetch_widgets_parallel(self, widget_configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return []
