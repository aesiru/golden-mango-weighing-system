#!/usr/bin/env python3
"""
System Setup Script
========================
CLI tool for complete backend bootstrap.

Usage:
    # Full bootstrap (database + tables + core seeds + optional first admin)
    python scripts/setup_system.py --all

    # Full bootstrap with explicit admin credentials
    python scripts/setup_system.py --all \
        --admin-username admin \
        --admin-email admin@example.com \
        --admin-full-name "System Administrator" \
        --admin-password "change-me"

    # Leave the system in first-run setup mode (frontend /setup page)
    python scripts/setup_system.py --all --skip-admin

    # Only create/migrate database tables
    python scripts/setup_system.py --db-only

    # Only run core seed pipeline (tables must already exist)
    python scripts/setup_system.py --seed-only

    # Only create first admin interactively via the same setup service flow
    python scripts/setup_system.py --superadmin-only --interactive

Run from the backend/ directory:
    cd backend && python scripts/setup_system.py --all
"""

import asyncio
import argparse
import getpass
import os
import sys
from dataclasses import dataclass

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine import make_url

# Resolve the backend/ directory so the app package is importable
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


# ── Helpers ──────────────────────────────────────────────────────────────────

@dataclass
class AdminCredentials:
    username: str
    email: str
    full_name: str
    password: str

def banner(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def step(msg: str) -> None:
    print(f"  ▶  {msg}")


def ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def skip(msg: str) -> None:
    print(f"  ⏭️   {msg}")


def fail(msg: str) -> None:
    print(f"  ❌  {msg}")


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def _resolve_bootstrap_database_url(arg_value: str | None) -> str | None:
    if arg_value:
        return arg_value

    env_value = os.getenv("DATABASE_BOOTSTRAP_URL")
    if env_value:
        return env_value

    return None


def _ensure_postgres_database_exists(*, target_url: str, bootstrap_url: str | None) -> None:
    target = make_url(target_url)
    if not str(target.drivername).startswith("postgresql"):
        skip("Database bootstrap skipped — non-PostgreSQL DATABASE_URL detected.")
        return

    if not target.database:
        raise RuntimeError("DATABASE_URL_SYNC must include a database name.")

    step(f"Ensuring PostgreSQL role and database exist for '{target.database}'...")
    bootstrap_failures: list[str] = []

    # Build a prioritised list of bootstrap URLs to try.
    # Each candidate is tried in order for BOTH connection AND privilege.
    # If a connection succeeds but the user lacks CREATE privilege, we
    # close it and move on to the next candidate rather than giving up.
    candidate_urls: list[str] = []
    if bootstrap_url:
        candidate_urls.append(bootstrap_url)
    else:
        # Try the app URL with the database switched to 'postgres'.
        # This works when the app role already exists and has CREATEDB privilege.
        app_as_admin = target.set(database="postgres")
        candidate_urls.append(app_as_admin.render_as_string(hide_password=False))

    # OS-user peer/trust auth — works on macOS Homebrew and Linux installs
    # where the current Unix user is a PostgreSQL superuser.
    candidate_urls.append("postgresql:///postgres")

    for url in candidate_urls:
        connection = None
        try:
            connection = psycopg2.connect(url)
        except Exception as exc:
            bootstrap_failures.append(f"connect {url!r}: {exc}")
            continue  # this candidate can't connect; try the next one

        connection.autocommit = True
        succeeded = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (target.username,))
                role_exists = cursor.fetchone() is not None

                if not role_exists:
                    if not target.password:
                        raise RuntimeError(
                            "DATABASE_URL_SYNC must include a password when the application role does not exist."
                        )
                    cursor.execute(
                        sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(target.username)),
                        (target.password,),
                    )
                    ok(f"Created PostgreSQL role '{target.username}'.")
                elif target.password:
                    cursor.execute(
                        sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(target.username)),
                        (target.password,),
                    )

                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target.database,))
                database_exists = cursor.fetchone() is not None

                if not database_exists:
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            sql.Identifier(target.database),
                            sql.Identifier(target.username),
                        )
                    )
                    ok(f"Created PostgreSQL database '{target.database}'.")
                else:
                    skip(f"Database '{target.database}' already exists.")

                cursor.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        sql.Identifier(target.database),
                        sql.Identifier(target.username),
                    )
                )
                succeeded = True
        except psycopg2.errors.InsufficientPrivilege:
            bootstrap_failures.append(f"insufficient privilege via {url!r}")
        finally:
            connection.close()

        if succeeded:
            return  # done — role and DB are ready

    # If bootstrap could not create anything, verify the target app connection anyway.
    # This still allows already-provisioned environments to pass without admin privileges.
    try:
        probe = psycopg2.connect(target_url)
    except Exception as exc:
        detail = "\n    - ".join(bootstrap_failures) if bootstrap_failures else "no bootstrap candidates succeeded"
        raise RuntimeError(
            "Unable to provision or reach the PostgreSQL application database. "
            "Set DATABASE_BOOTSTRAP_URL (or --bootstrap-db-url) to a superuser connection string, "
            "or pre-create the role and database before running setup.\n"
            f"Target database: {target.database}\n"
            f"Target role: {target.username}\n"
            f"App connection error: {exc}\n"
            f"Bootstrap attempts:\n    - {detail}"
        ) from exc
    else:
        probe.close()
        skip(
            "Bootstrap connection did not have privilege to create the role/database, "
            "but the application database is already reachable. Continuing."
        )


def _resolve_admin_credentials(args: argparse.Namespace, *, required: bool) -> AdminCredentials | None:
    provided_values = [
        args.admin_username,
        args.admin_email,
        args.admin_full_name,
        args.admin_password,
    ]
    provided_count = sum(1 for value in provided_values if value)

    if provided_count not in (0, 4):
        raise ValueError(
            "Admin credentials must be provided as a complete set: "
            "--admin-username, --admin-email, --admin-full-name, --admin-password."
        )

    if provided_count == 4:
        return AdminCredentials(
            username=args.admin_username,
            email=args.admin_email,
            full_name=args.admin_full_name,
            password=args.admin_password,
        )

    if args.skip_admin:
        return None

    if args.interactive or (_is_interactive() and required):
        print("\n  Enter first administrator credentials:")
        username = input("    Username  : ").strip()
        email = input("    Email     : ").strip()
        full_name = input("    Full name : ").strip()
        password = getpass.getpass("    Password  : ")
        if not all([username, email, full_name, password]):
            raise ValueError("All administrator fields are required.")
        return AdminCredentials(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
        )

    if required:
        return None

    return None


# ── Steps ─────────────────────────────────────────────────────────────────────

async def step_init_db(bootstrap_url: str | None) -> None:
    """Ensure all database tables exist (creates missing tables, no destructive ops)."""
    from app.core.loader import load_modules
    from app.entities import load_all_entities
    from app.infrastructure.metadata.integrity import validate_loaded_metadata_and_models
    from app.infrastructure.database.repositories.entity_repository import register_core_models
    from app.core.database import init_db
    from app.core.config import settings

    _ensure_postgres_database_exists(
        target_url=settings.sync_database_url,
        bootstrap_url=bootstrap_url,
    )

    step("Loading modules and entity metadata...")
    load_modules()
    load_all_entities()
    register_core_models()

    step("Validating entity metadata against loaded models...")
    validate_loaded_metadata_and_models()
    ok("Metadata and model integrity verified.")

    step("Initialising database tables...")
    await init_db()
    ok("Database tables ready.")


async def step_seed(db) -> None:
    """Run the full modular core seed pipeline."""
    from app.core.seeds import run_all_seeds
    step("Running seed pipeline...")
    summary = await run_all_seeds(db)
    ok(f"Seeding complete — {summary.total_created} records created, {summary.total_skipped} skipped.")


async def step_superadmin(db, credentials: AdminCredentials | None) -> None:
    """Create the first admin via the SetupService flow if credentials were provided."""
    from app.core.framework.models.auth import User
    from app.application.services.setup_service import SetupService

    svc = SetupService(db)
    status = await svc.get_status()

    if status.is_setup_complete:
        skip(f"Superadmin already exists ({status.user_count} user(s) in DB). Skipping.")
        return

    if credentials is None:
        skip(
            "No administrator credentials were provided. Leaving the system in first-run setup mode. "
            "Open the frontend and complete /setup, or rerun with admin flags."
        )
        return

    try:
        user = await svc.create_superadmin(
            username=credentials.username,
            email=credentials.email,
            full_name=credentials.full_name,
            password=credentials.password,
        )
        ok(f"Superadmin '{user.username}' ({user.email}) created.")
    except ValueError as exc:
        skip(str(exc))


# ── Main entry ────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    from app.core.database import async_session_maker

    run_db        = args.all or args.db_only
    run_seeds     = args.all or args.seed_only
    run_superadmin = args.all or args.superadmin_only
    bootstrap_url = _resolve_bootstrap_database_url(args.bootstrap_db_url)

    admin_required = bool(run_superadmin)
    admin_credentials = _resolve_admin_credentials(args, required=admin_required and not args.skip_admin)

    if not any([run_db, run_seeds, run_superadmin]):
        print("Nothing to do. Use --all, --db-only, --seed-only, or --superadmin-only.")
        return

    # DB init must happen before seeding / superadmin
    if run_db or run_seeds or run_superadmin:
        await step_init_db(bootstrap_url)

    async with async_session_maker() as db:
        if run_seeds:
            await step_seed(db)

        if run_superadmin:
            await step_superadmin(db, admin_credentials)

    print()
    ok("Setup complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EAM backend bootstrap — database init, core seeding, and optional first-admin creation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all",             action="store_true", help="Run full setup pipeline")
    group.add_argument("--db-only",         action="store_true", help="Only init DB tables")
    group.add_argument("--seed-only",       action="store_true", help="Only run the core seed pipeline")
    group.add_argument("--superadmin-only", action="store_true", help="Only create the first administrator")
    parser.add_argument("--interactive",    action="store_true", help="Prompt for administrator credentials")
    parser.add_argument("--skip-admin",     action="store_true", help="Do not create the first administrator during --all")
    parser.add_argument("--admin-username", help="First administrator username")
    parser.add_argument("--admin-email",    help="First administrator email")
    parser.add_argument("--admin-full-name", help="First administrator full name")
    parser.add_argument("--admin-password", help="First administrator password")
    parser.add_argument(
        "--bootstrap-db-url",
        help="PostgreSQL admin URL used to create the application role/database. Falls back to DATABASE_BOOTSTRAP_URL or DATABASE_URL_SYNC with the database switched to 'postgres'.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    banner("System Setup")
    asyncio.run(main(parse_args()))
