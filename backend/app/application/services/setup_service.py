"""
Setup Service
=============
Application-layer service for first-time system setup.

Responsibilities:
- Check whether initial setup has been completed
- Create the first superadmin user
- Run the full initial seed pipeline

Follows CLEAN Architecture: depends on domain models and seed modules,
not on HTTP concerns. Controllers (setup.py) call this.
"""
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.framework.models.auth import User
from app.core.seeds import run_all_seeds, SeedSummary


@dataclass
class SetupStatus:
    is_setup_complete: bool
    needs_setup: bool
    user_count: int


@dataclass
class SetupResult:
    admin_username: str
    admin_email: str
    admin_full_name: str
    seed_summary: SeedSummary | None = None


class SetupService:
    """Service for orchestrating first-run system initialization."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Queries ──────────────────────────────────────────────────────

    async def get_status(self) -> SetupStatus:
        """Return current setup status (whether users exist)."""
        count_result = await self._db.execute(
            select(func.count()).select_from(User)
        )
        user_count = count_result.scalar() or 0
        return SetupStatus(
            is_setup_complete=user_count > 0,
            needs_setup=user_count == 0,
            user_count=user_count,
        )

    # ── Commands ─────────────────────────────────────────────────────

    async def create_superadmin(
        self,
        *,
        username: str,
        email: str,
        full_name: str,
        password: str,
    ) -> User:
        """
        Create the first superadmin user.
        Raises ValueError if setup is already complete (users exist).
        Raises ValueError if the username is already taken.
        """
        status = await self.get_status()
        if status.is_setup_complete:
            raise ValueError(
                "Setup already completed. An administrator account already exists."
            )

        from app.core.seeds.users import seed_superadmin
        return await seed_superadmin(
            self._db,
            username=username,
            email=email,
            full_name=full_name,
            password=password,
        )

    async def run_initial_setup(
        self,
        *,
        username: str,
        email: str,
        full_name: str,
        password: str,
        run_seeds: bool = True,
    ) -> SetupResult:
        """
        Full first-run pipeline:
          1. Create superadmin
          2. Optionally run all seeds (roles, workflow, reference data)

        Raises ValueError if setup is already complete.
        """
        user = await self.create_superadmin(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
        )

        seed_summary: SeedSummary | None = None
        if run_seeds:
            seed_summary = await run_all_seeds(self._db)

        return SetupResult(
            admin_username=user.username,
            admin_email=user.email,
            admin_full_name=user.full_name,
            seed_summary=seed_summary,
        )
