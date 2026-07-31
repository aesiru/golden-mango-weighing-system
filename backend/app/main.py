import time
import logging
from contextlib import asynccontextmanager
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.config import settings
from app.core.database import init_db, async_session_maker
from app.core.seed import run_seeds
from app.core.loader import load_modules
from app.core.exceptions import register_exception_handlers
from app.entities import load_all_entities
from app.application.services.notifications.socketio import sio
from app.api.router import MODULE_LABELS

# Configure slow_queries logger
logging.getLogger("slow_queries").setLevel(logging.WARNING)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        if duration > 0.5:  # log anything over 500ms
            print(f"SLOW REQUEST: {request.method} {request.url.path} took {duration*1000:.0f}ms")
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all module models (dynamic)
    load_modules()
    # Load entity metadata
    load_all_entities()
    
    # Register core models with the entity repository
    from app.infrastructure.database.repositories.entity_repository import register_core_models
    register_core_models()
    
    # Server actions and hooks are now auto-discovered by the module loader
    # via hooks.py register_hooks() in each module
    
    # Core models (auth, workflow) are registered by register_core_models()
    
    await init_db()
    if settings.RUN_SEEDS:
        async with async_session_maker() as db:
            await run_seeds(db)
    
    # Register scheduled jobs from all modules (decoupled from scheduler)
    # Note: All modules removed - no scheduled jobs to register
    # Future modules can register jobs via their hooks.py files

    # Initialize scheduler through application service
    from app.application.services.scheduling.app_initialization_service import AppInitializationService
    app_init_service = AppInitializationService()
    app_init_service.initialize_scheduler()

    # Start MQTT weight-reading subscriber (ESP32 scales)
    from app.infrastructure.mqtt.mqtt_client import MqttWeightSubscriber
    mqtt_subscriber = MqttWeightSubscriber()
    await mqtt_subscriber.start()

    yield

    # Shutdown MQTT subscriber
    await mqtt_subscriber.stop()

    # Shutdown scheduler on app exit
    app_init_service.shutdown_scheduler()


fastapi_app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {"name": v["label"], "description": v["description"]}
        for v in MODULE_LABELS.values()
    ] + [
        {"name": "Entities", "description": "Generic entity CRUD kernel (all entities share these paths at runtime)."},
        {"name": "System",   "description": "Authentication, user management, workflows, and infrastructure endpoints."},
        {"name": "Features", "description": "Product features: diagram, calendar, search, comments, and more."},
        {"name": "App",      "description": "Cross-domain platform features: branding."},
        {"name": "Services", "description": "Shared service utilities: notifications and email."},
    ],
)

# Register custom exception handlers
register_exception_handlers(fastapi_app)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
)

fastapi_app.add_middleware(TimingMiddleware)
fastapi_app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Consolidated API routes
from app.api.router import api_router

# Register master router
fastapi_app.include_router(api_router, prefix="/api")


@fastapi_app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@fastapi_app.get("/health")
async def health():
    from sqlalchemy import text
    from app.core.database import async_session_maker

    db_ok = False
    db_version = None
    try:
        async with async_session_maker() as session:
            row = await session.execute(text("SELECT version()"))
            db_version = row.scalar()
            db_ok = True
    except Exception as e:
        db_version = str(e)

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": {"connected": db_ok, "version": db_version},
    }


# ---------------------------------------------------------------------------
# Custom OpenAPI schema — virtualises entity paths per module for /docs
# ---------------------------------------------------------------------------

def _custom_openapi():
    """
    Post-process the generated OpenAPI schema so that ``/docs`` groups entity
    routes by business module instead of showing a flat "Entities" list.

    Strategy
    --------
    1. Generate the base schema with FastAPI's default helper.
    2. For every entity in MetaRegistry, duplicate all ``/entity/{entity}/...``
       path templates to concrete paths (e.g. ``/entity/asset/list``), tagged
       with the entity's module label and given a human-readable summary.
    3. Remove the original generic ``/entity/{entity}/...`` paths from the spec
       so Swagger shows only the expanded, module-grouped paths.

    Runtime routing is **unchanged** — only documentation is affected.
    """
    if fastapi_app.openapi_schema:
        return fastapi_app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    import copy

    from app.meta.registry import MetaRegistry
    from app.api.router import MODULE_LABELS as _MODULE_LABELS

    schema = get_openapi(
        title=fastapi_app.title,
        version=fastapi_app.version,
        description=fastapi_app.description,
        routes=fastapi_app.routes,
        tags=fastapi_app.openapi_tags,
    )

    original_paths: dict = schema.get("paths", {})
    entity_path_templates: dict[str, dict] = {}
    non_entity_paths: dict[str, dict] = {}

    for path, path_item in original_paths.items():
        if "/{entity}" in path:
            entity_path_templates[path] = path_item
        else:
            non_entity_paths[path] = path_item

    expanded_paths: dict[str, dict] = {}

    # Pre-build read schema JSON schemas for GET response injection
    _read_schemas: dict[str, dict] = {}
    for em in MetaRegistry.list_all():
        rs = MetaRegistry.get_read_schema(em.name)
        if rs is not None:
            try:
                _read_schemas[em.name] = rs.model_json_schema()
            except Exception:
                pass

    for entity_meta in MetaRegistry.list_all():
        module_info = _MODULE_LABELS.get(entity_meta.module)
        tag = module_info["label"] if module_info else entity_meta.module.replace("_", " ").title()
        human_label = entity_meta.label or entity_meta.name.replace("_", " ").title()
        read_json_schema = _read_schemas.get(entity_meta.name)

        for template_path, path_item in entity_path_templates.items():
            concrete_path = template_path.replace("{entity}", entity_meta.name)
            cloned_item = copy.deepcopy(path_item)

            for method, method_item in cloned_item.items():
                if not isinstance(method_item, dict):
                    continue
                # Replace generic "Entities" tag with the module tag
                method_item["tags"] = [tag]
                # Build a human-readable summary
                suffix = template_path.replace("/entity/{entity}", "").lstrip("/")
                if not suffix:
                    suffix = "action"
                method_item["summary"] = f"{human_label} — {suffix.replace('/', ' ').replace('-', ' ').title()}"
                # Remove the now-redundant {entity} path parameter entry
                method_item["parameters"] = [
                    p for p in method_item.get("parameters", [])
                    if not (isinstance(p, dict) and p.get("name") == "entity")
                ]
                # Inject read schema into GET 200 responses for richer Swagger docs
                if method.lower() == "get" and read_json_schema is not None:
                    success_resp = method_item.setdefault("responses", {}).setdefault("200", {})
                    success_resp.setdefault("description", "Successful response")
                    success_resp["content"] = {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string", "example": "success"},
                                    "data": read_json_schema,
                                },
                            }
                        }
                    }

            expanded_paths[concrete_path] = cloned_item

    schema["paths"] = {**non_entity_paths, **expanded_paths}

    fastapi_app.openapi_schema = schema
    return fastapi_app.openapi_schema


fastapi_app.openapi = _custom_openapi  # type: ignore[method-assign]


app = socketio.ASGIApp(sio, fastapi_app)