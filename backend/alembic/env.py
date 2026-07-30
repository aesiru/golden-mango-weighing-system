from logging.config import fileConfig
import importlib
import pkgutil
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the backend directory to the path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import base + settings (avoid loading full app stack)
from app.core.database import Base
from app.core.config import settings


def _load_models_only():
    """Import model files to register them with Base.metadata.

    Order matters:
      1. app/core/framework/models/* first  (auth, workflow, etc. - owns reserved tables)
      2. app/modules/*/models/* second  (entity models that may FK into ^)
    Each import is wrapped so one broken file doesn't abort the whole run.
    """
    # 1. Core framework models (auth, workflow, ordering, infrastructure, ...)
    core_models_path = BACKEND_DIR / "app" / "core" / "framework" / "models"
    if core_models_path.exists():
        for _, mod, _ in pkgutil.iter_modules([str(core_models_path)]):
            if mod == "__init__":
                continue  # Skip __init__.py
            try:
                importlib.import_module(f"app.core.framework.models.{mod}")
            except Exception as exc:
                print(f"  \u26a0 skip app.core.framework.models.{mod}: {exc}")

    # 2. Per-module entity models
    modules_path = BACKEND_DIR / "app" / "modules"
    if modules_path.exists():
        for _, module_name, _ in pkgutil.iter_modules([str(modules_path)]):
            models_dir = modules_path / module_name / "models"
            if not models_dir.exists():
                continue
            for _, model_file, _ in pkgutil.iter_modules([str(models_dir)]):
                fqn = f"app.modules.{module_name}.models.{model_file}"
                try:
                    importlib.import_module(fqn)
                except Exception as exc:
                    print(f"  \u26a0 skip {fqn}: {exc}")


_load_models_only()

# Set the database URL from settings
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
