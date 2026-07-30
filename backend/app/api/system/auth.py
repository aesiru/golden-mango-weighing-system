"""
Authentication routes for login/logout.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
import bcrypt
from jose import jwt

from app.core.database import get_db
from app.core.config import settings
from app.core.framework.models.auth import User, Role
from app.api.system.meta import get_meta_list, MODULE_ICONS, MODULE_LABELS, _module_order_key

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user from core_users table only."""
    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles))
    )
    return result.scalar_one_or_none()


DEFAULT_MODULE_ICON = "i-lucide-folder"
DEFAULT_ENTITY_ICON = "i-lucide-file-text"
ICON_ALIASES = {
    "tool": "wrench",
    "file-invoice": "file-text",
    "palm-tree": "tree-palm",
}


def _format_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _normalize_icon_name(icon: str | None) -> str | None:
    if not icon:
        return None

    normalized = ICON_ALIASES.get(icon, icon).strip()
    if not normalized:
        return None
    if normalized.startswith("i-lucide-"):
        return normalized
    if normalized.startswith("lucide:"):
        return f'i-{normalized.replace(":", "-")}'
    return f"i-lucide-{normalized}"


def _entity_nav_item(entity: dict, fallback_icon: str) -> dict:
    return {
        "label": entity["label"],
        "icon": _normalize_icon_name(entity.get("icon")) or fallback_icon or DEFAULT_ENTITY_ICON,
        "to": f'/{entity["name"]}',
        "entity": entity["name"],
    }


def _group_sort_key(group_label: str, group_entities: list[dict]) -> tuple[int, str]:
    first_entity_order = min(
        (
            entity.get("_sidebar_order", idx)
            for idx, entity in enumerate(group_entities)
        ),
        default=999,
    )
    return (first_entity_order, group_label.lower())


def _build_sidebar_navigation(sidebar_entities: list[dict]) -> list[dict]:
    modules: dict[str, dict] = {}
    module_sequence: list[str] = []

    for idx, raw_entity in enumerate(sidebar_entities):
        entity = {**raw_entity, "_sidebar_order": idx}
        module_key = (entity.get("module") or "other").strip() or "other"
        if module_key not in modules:
            modules[module_key] = {
                "key": module_key,
                "groups": {},
                "ungrouped": [],
            }
            module_sequence.append(module_key)
        module = modules[module_key]

        group_label = (entity.get("group") or "").strip()
        if group_label:
            module["groups"].setdefault(group_label, []).append(entity)
        else:
            module["ungrouped"].append(entity)

    navigation: list[dict] = []

    for module_key in module_sequence:
        module = modules[module_key]
        module_order_key = _module_order_key(module_key)
        module_label = MODULE_LABELS.get(module_order_key, _format_label(module_key))
        module_icon = _normalize_icon_name(MODULE_ICONS.get(module_order_key)) or DEFAULT_MODULE_ICON
        items: list[dict] = []

        for entity in module["ungrouped"]:
            items.append({
                "type": "entity",
                **_entity_nav_item(entity, module_icon),
            })

        grouped_labels = sorted(
            module["groups"],
            key=lambda group_label: _group_sort_key(group_label, module["groups"][group_label]),
        )
        for group_label in grouped_labels:
            group_entities = module["groups"][group_label]
            children = [_entity_nav_item(entity, module_icon) for entity in group_entities]
            if not children:
                continue
            items.append({
                "type": "group",
                "label": group_label,
                "icon": module_icon,
                "children": children,
                "defaultOpen": True,
            })

        if items:
            navigation.append({
                "key": module["key"].replace(" ", "_").lower(),
                "label": module_label,
                "icon": module_icon,
                "items": items,
            })

    return navigation


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return access token."""
    user = await get_user_by_username(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
        path="/",
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "roles": [r.name for r in user.roles],
        },
    }


@router.post("/boot")
async def boot_info(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return complete boot info including sidebar entities."""
    user = await get_user_by_username(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        max_age=int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
        path="/",
    )
    
    # Get sidebar entities
    meta_response = await get_meta_list(db=db, authorization=f"Bearer {access_token}")
    meta_list = meta_response.get("data", [])
    
    sidebar_entities = [m for m in meta_list if m.get("in_sidebar", False)]
    navigation = _build_sidebar_navigation(sidebar_entities)
    
    # Get allowed dashboards
    from app.core.security import CurrentUser
    from app.application.services.dashboards.dashboard_service import DASHBOARD_DEFINITIONS, DASHBOARD_ORDER, WIDGET_DASHBOARD_MAP
    from app.infrastructure.database.repositories.dashboard_repository import DashboardRepository
    from app.application.services.dashboards.dashboard_service import DashboardAppService
    
    current_user = CurrentUser(
        id=str(user.id),
        username=user.username,
        is_superuser=user.is_superuser,
        roles=[r.name for r in user.roles]
    )
    dashboard_repo = DashboardRepository(db)
    dashboard_service = DashboardAppService(dashboard_repo, current_user)
    widget_configs = dashboard_service.resolve_user_widgets()
    
    # Resolve allowed dashboards (same logic as in operational_dashboard.py)
    if current_user.is_superuser:
        keys = DASHBOARD_ORDER
    else:
        discovered = {
            WIDGET_DASHBOARD_MAP[cfg["type"]]
            for cfg in widget_configs
            if cfg["type"] in WIDGET_DASHBOARD_MAP
        }
        keys = [key for key in DASHBOARD_ORDER if key in discovered]
    
    allowed_dashboards = [
        {
            "key": key,
            "label": DASHBOARD_DEFINITIONS[key]["label"],
            "description": DASHBOARD_DEFINITIONS[key]["description"],
            "icon": DASHBOARD_DEFINITIONS[key]["icon"],
        }
        for key in keys
    ]
    
    # Add stats and charts to each allowed dashboard from DASHBOARD_DEFINITIONS
    allowed_dashboards_with_config = []
    for dashboard in allowed_dashboards:
        definition = DASHBOARD_DEFINITIONS.get(dashboard["key"])
        if definition:
            allowed_dashboards_with_config.append({
                **dashboard,
                "stats": definition.get("stats", []),
                "charts": definition.get("charts", []),
            })
        else:
            allowed_dashboards_with_config.append(dashboard)
    
    # Get workflow states
    from app.core.framework.models.workflow import WorkflowState
    from sqlalchemy import select
    result = await db.execute(select(WorkflowState).order_by(WorkflowState.label.asc()))
    workflow_states = [
        {"id": s.id, "label": s.label, "slug": s.slug, "color": s.color}
        for s in result.scalars().all()
    ]
    
    # Get branding settings
    from pathlib import Path
    from app.infrastructure.settings import BrandingStore
    from app.application.services.branding_service import BrandingService
    uploads_root = Path(settings.UPLOAD_DIR)
    settings_dir = uploads_root / "settings"
    branding_service = BrandingService(
        store=BrandingStore(settings_dir / "branding.json"),
        assets_dir=settings_dir / "branding",
        uploads_root=uploads_root,
    )
    branding_settings = branding_service.get_branding()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "roles": [r.name for r in user.roles],
        },
        "sidebar": {
            "entities": sidebar_entities,
            "navigation": navigation,
        },
        "allowed_dashboards": allowed_dashboards_with_config,
        "workflow_states": workflow_states,
        "branding_settings": branding_settings,
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token from cookie."""
    cookie_refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not cookie_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = jwt.decode(cookie_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        result = await db.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        new_access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.get("/validate")
async def validate_token(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Validate current access token and return user info."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        result = await db.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        return {
            "status": "success",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_superuser": user.is_superuser,
                "roles": [r.name for r in user.roles],
            },
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.get("/me")
async def auth_me(
    request: Request,
    response: Response,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Single-request auth check for app startup.
    
    Accepts either a valid access token (Authorization header) or a refresh
    token (httponly cookie). Returns user info and, when the access token was
    expired but a valid refresh cookie existed, issues a new access token in
    the response so the client can update its store in one round-trip.
    """
    user = None
    new_token = None

    # 1. Try access token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username = payload.get("sub")
            if username:
                result = await db.execute(
                    select(User)
                    .where(User.username == username)
                    .options(selectinload(User.roles))
                )
                user = result.scalar_one_or_none()
                if user and not user.is_active:
                    user = None
        except jwt.JWTError:
            user = None  

    # 2. If access token failed, try refresh cookie
    if user is None:
        cookie_refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if cookie_refresh_token:
            try:
                payload = jwt.decode(cookie_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                if payload.get("type") == "refresh":
                    username = payload.get("sub")
                    if username:
                        result = await db.execute(
                            select(User)
                            .where(User.username == username)
                            .options(selectinload(User.roles))
                        )
                        user = result.scalar_one_or_none()
                        if user and not user.is_active:
                            user = None
                        elif user:
                            # Issue new access token
                            new_token = create_access_token(
                                data={"sub": user.username, "user_id": user.id}
                            )
            except (jwt.ExpiredSignatureError, jwt.JWTError):
                user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_superuser": user.is_superuser,
        "roles": [r.name for r in user.roles],
    }

    resp = {"status": "success", "user": user_data}
    if new_token:
        resp["new_token"] = new_token
    return resp
