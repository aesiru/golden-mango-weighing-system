"""
Position Diagram Feature
========================
Graph diagram endpoints — returns data shaped to match the frontend
CustomGraphNode / CustomGraphLink types in data.ts.

Node type mapping:
  position.asset_class_name → CustomGraphNodeType (best-effort, fallback "resource")

Loading strategy:
  GET /diagram/locations  — returns nodes (id, label, subLabel, type) and
                            links (source, target, showFlow, showArrow)
  CRUD /diagram/layouts   — user-saved named views.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.core.serialization import record_to_dict
from app.core.exceptions import ForbiddenError
from app.core.framework.models.infrastructure import DiagramLayout
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service
from app.infrastructure.database.repositories.entity_repository import get_entity_model

router = APIRouter(tags=["features"])

_NONE_LOC_ID = "__none"

# ---------------------------------------------------------------------------
# CustomGraphNodeType values (mirrors frontend data.ts enum)
# ---------------------------------------------------------------------------
_NODE_TYPE_IDENTITY = "identity"
_NODE_TYPE_NETWORK = "network"
_NODE_TYPE_RESOURCE = "resource"
_NODE_TYPE_COMPUTE = "compute"
_NODE_TYPE_SECRET = "secret"
_NODE_TYPE_FINDING = "finding"
_NODE_TYPE_THREAT_ACTOR = "threat-actor"

_ASSET_CLASS_TYPE_KEYWORDS: list[tuple[list[str], str]] = [
    (["sensor", "instrument", "transmitter", "meter", "gauge", "detector"], _NODE_TYPE_NETWORK),
    (["pump", "motor", "compressor", "turbine", "engine", "fan", "blower"], _NODE_TYPE_COMPUTE),
    (["valve", "actuator", "switch", "relay", "damper"], _NODE_TYPE_IDENTITY),
    (["tank", "vessel", "container", "silo", "drum", "reactor"], _NODE_TYPE_SECRET),
    (["pipe", "duct", "line", "conveyor", "belt"], _NODE_TYPE_NETWORK),
]


def _map_asset_class_to_node_type(asset_class_name: Optional[str]) -> str:
    """Map an asset class name to a CustomGraphNodeType string (best-effort)."""
    if not asset_class_name:
        return _NODE_TYPE_RESOURCE
    lower = asset_class_name.lower()
    for keywords, node_type in _ASSET_CLASS_TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return node_type
    return _NODE_TYPE_RESOURCE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attachment_path_to_public_url(file_path: Optional[str]) -> Optional[str]:
    if not file_path:
        return None
    path = Path(file_path)
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    try:
        relative_path = path.resolve().relative_to(upload_root)
    except ValueError:
        return None
    return f"/uploads/{relative_path.as_posix()}"


async def _check_position_permissions(
    user: Any,
    rbac: RBACAppService,
) -> None:
    """Raise ForbiddenError if user lacks position/position_relation read perms."""
    if not await rbac.check_permission(
        user_id=user.id,
        entity="position",
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    ):
        raise ForbiddenError("You don't have permission to access positions")

    if not await rbac.check_permission(
        user_id=user.id,
        entity="position_relation",
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    ):
        raise ForbiddenError("You don't have permission to access position relations")


# ---------------------------------------------------------------------------
# 1. Diagram data — nodes and links matching CustomGraphNode / CustomGraphLink
# ---------------------------------------------------------------------------

_GROUP_NO_CONNECTIONS = "No Connections"
_GROUP_UNASSIGNED = "Unassigned"


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


@router.get("/diagram/locations", name="get_diagram_locations")
async def get_diagram_locations(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """
    Returns graph data for Unovis VisGraph with ELK hierarchical layout.

    Node classification (priority order):
      1. No location                           → group/subGroup = "Unassigned"
      2. Has location, no position_relations   → group/subGroup = "No Connections"
            3. Has location + connections            → locationPath = full root→leaf hierarchy

    Response:
    {
            "status": "success",
            "nodes": [{id, group, subGroup, label, shape, icon, nodeType, locationPath, locationPathIds}],
            "links": [{source, target}],
            "panels": [{nodes, label, locationId, panelType, borderWidth, padding, dashedOutline}],
            "groupOrder": [<root group names in display order>],
            "maxLocationDepth": number
    }
    """
    user = await get_current_user_from_token(authorization, db)
    await _check_position_permissions(user, rbac)

    position_model = get_entity_model("position")
    relation_model = get_entity_model("position_relation")
    location_model = get_entity_model("location")
    if not position_model or not relation_model or not location_model:
        return {"status": "error", "message": "Models not found"}

    # ------------------------------------------------------------------
    # 1. Fetch locations → build lookup tables
    # ------------------------------------------------------------------
    location_result = await db.execute(select(location_model).limit(500))
    location_id_to_name: dict[str, str] = {}
    location_id_to_parent: dict[str, Optional[str]] = {}

    for loc in location_result.scalars().all():
        ld = record_to_dict(loc)
        location_id_to_name[ld["id"]] = ld.get("name") or ld["id"]
        location_id_to_parent[ld["id"]] = ld.get("parent_location") or None

    def _get_location_id_path(location_id: str) -> list[str]:
        path_ids: list[str] = []
        seen: set[str] = set()
        current_id: Optional[str] = location_id
        while current_id and current_id not in seen and current_id in location_id_to_name:
            seen.add(current_id)
            path_ids.append(current_id)
            current_id = location_id_to_parent.get(current_id)
        path_ids.reverse()
        return path_ids

    def _get_location_name_path(location_id: str) -> list[str]:
        return [location_id_to_name[loc_id] for loc_id in _get_location_id_path(location_id)]

    # ------------------------------------------------------------------
    # 2. Fetch ALL relations first → track which positions are connected
    # ------------------------------------------------------------------
    rel_result = await db.execute(select(relation_model).limit(1000))
    raw_relations: list[tuple[str, str]] = []
    connected_position_ids: set[str] = set()

    for rel in rel_result.scalars().all():
        rd = record_to_dict(rel)
        src, tgt = rd.get("position_a"), rd.get("position_b")
        if src and tgt:
            raw_relations.append((src, tgt))
            connected_position_ids.add(src)
            connected_position_ids.add(tgt)

    # ------------------------------------------------------------------
    # 3. Fetch positions → collect all data
    # ------------------------------------------------------------------
    position_result = await db.execute(select(position_model).limit(500))
    all_positions: list[dict] = []
    position_location_map: dict[str, str] = {}  # pos_id → location_id
    position_asset_ids: dict[str, str] = {}       # pos_id → asset_id

    for pos in position_result.scalars().all():
        d = record_to_dict(pos)
        all_positions.append(d)
        loc_id = d.get("location") or None
        if loc_id and loc_id in location_id_to_name:
            position_location_map[d["id"]] = loc_id
        asset_id = d.get("current_asset")
        if asset_id:
            position_asset_ids[d["id"]] = asset_id

    all_position_ids: set[str] = {p["id"] for p in all_positions}

    # ------------------------------------------------------------------
    # 4. Fetch asset tags for labels
    # ------------------------------------------------------------------
    asset_model = get_entity_model("asset")
    asset_id_to_tag: dict[str, str] = {}
    if asset_model and position_asset_ids:
        asset_ids = set(position_asset_ids.values())
        asset_result = await db.execute(
            select(asset_model).where(asset_model.id.in_(asset_ids))
        )
        for asset in asset_result.scalars().all():
            ad = record_to_dict(asset)
            asset_id_to_tag[ad["id"]] = ad.get("asset_tag") or ""

    # ------------------------------------------------------------------
    # 5. Classify each position and build nodes
    # ------------------------------------------------------------------
    def _build_label(pos: dict) -> str:
        position_tag = pos.get("position_tag") or pos["id"]
        asset_class_name = pos.get("asset_class_name") or ""
        asset_tag = asset_id_to_tag.get(position_asset_ids.get(pos["id"], ""), "")
        if asset_class_name or asset_tag:
            parts = []
            if asset_class_name:
                parts.append(f"[{asset_class_name}]")
            parts.append(position_tag)
            if asset_tag:
                parts.append(f"({asset_tag})")
            return " ".join(parts)
        return position_tag

    nodes: list[dict] = []
    location_panel_node_ids: dict[str, list[str]] = {}
    special_panel_node_ids: dict[str, list[str]] = {
        _GROUP_NO_CONNECTIONS: [],
        _GROUP_UNASSIGNED: [],
    }
    max_location_depth = 1

    for pos in all_positions:
        pos_id = pos["id"]
        label = _build_label(pos)
        loc_id = position_location_map.get(pos_id)
        is_connected = pos_id in connected_position_ids
        location_path: list[str] = []
        location_path_ids: list[str] = []

        if loc_id is None:
            group = _GROUP_UNASSIGNED
            subgroup = _GROUP_UNASSIGNED
            node_type = "unassigned"
            location_path = [_GROUP_UNASSIGNED]
        elif not is_connected:
            group = _GROUP_NO_CONNECTIONS
            subgroup = _GROUP_NO_CONNECTIONS
            node_type = "no-connections"
            location_path = [_GROUP_NO_CONNECTIONS]
        else:
            location_path_ids = _get_location_id_path(loc_id)
            location_path = [location_id_to_name[location_id] for location_id in location_path_ids]
            group = location_path[0]
            subgroup = location_path[-1]
            node_type = "placed"
            max_location_depth = max(max_location_depth, len(location_path))

            for ancestor_id in location_path_ids:
                location_panel_node_ids.setdefault(ancestor_id, []).append(pos_id)

        if node_type == "unassigned":
            special_panel_node_ids[_GROUP_UNASSIGNED].append(pos_id)
        elif node_type == "no-connections":
            special_panel_node_ids[_GROUP_NO_CONNECTIONS].append(pos_id)

        nodes.append({
            "id": pos_id,
            "group": group,
            "subGroup": subgroup,
            "label": label,
            "shape": "Square",
            "icon": "\uf0ac",
            "nodeType": node_type,
            "locationPath": location_path,
            "locationPathIds": location_path_ids,
            "locationId": loc_id,
        })

    # ------------------------------------------------------------------
    # 6. Build panels — one per location subtree + special groups
    # ------------------------------------------------------------------
    panels: list[dict] = []

    def _panel_depth(location_id: str) -> int:
        return len(_get_location_id_path(location_id))

    for location_id, node_ids in sorted(
        location_panel_node_ids.items(),
        key=lambda item: (_panel_depth(item[0]), location_id_to_name[item[0]]),
    ):
        if not node_ids:
            continue
        depth = _panel_depth(location_id)
        panels.append({
            "nodes": _unique_preserve_order(node_ids),
            "label": location_id_to_name[location_id],
            "locationId": location_id,
            "panelType": "location",
            "borderWidth": 5 if depth == 1 else 3,
            "padding": 22 if depth == 1 else 14,
            "dashedOutline": False,
        })

    for special_group, node_ids in special_panel_node_ids.items():
        if not node_ids:
            continue
        panels.append({
            "nodes": _unique_preserve_order(node_ids),
            "label": special_group,
            "locationId": None,
            "panelType": "special",
            "borderWidth": 2,
            "padding": 15,
            "dashedOutline": True,
        })

    # ------------------------------------------------------------------
    # 7. Build links (only between known positions)
    # ------------------------------------------------------------------
    links: list[dict] = [
        {"source": src, "target": tgt}
        for src, tgt in raw_relations
        if src in all_position_ids and tgt in all_position_ids
    ]

    # ------------------------------------------------------------------
    # 8. Build group order: sorted location groups, then special groups
    # ------------------------------------------------------------------
    location_groups: set[str] = set()
    for node in nodes:
        if node["nodeType"] == "placed":
            location_groups.add(node["group"])

    group_order = sorted(location_groups) + [_GROUP_NO_CONNECTIONS, _GROUP_UNASSIGNED]

    return {
        "status": "success",
        "nodes": nodes,
        "links": links,
        "panels": panels,
        "groupOrder": group_order,
        "maxLocationDepth": max_location_depth,
    }


# ---------------------------------------------------------------------------
# 2. Diagram layout CRUD (named saved views)
# ---------------------------------------------------------------------------

class DiagramLayoutCreate(BaseModel):
    name: str
    filters: Optional[dict[str, Any]] = None


class DiagramLayoutUpdate(BaseModel):
    name: Optional[str] = None
    filters: Optional[dict[str, Any]] = None


@router.get("/diagram/layouts", name="list_diagram_layouts")
async def list_diagram_layouts(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user_from_token(authorization, db)
    result = await db.execute(
        select(DiagramLayout)
        .where(DiagramLayout.created_by == user.id)
        .order_by(DiagramLayout.created_at)
    )
    return {
        "status": "success",
        "layouts": [
            {
                "id": layout.id,
                "name": layout.name,
                "filters": json.loads(layout.filters) if layout.filters else {},
                "created_at": layout.created_at.isoformat() if layout.created_at else None,
                "updated_at": layout.updated_at.isoformat() if layout.updated_at else None,
            }
            for layout in result.scalars().all()
        ],
    }


@router.post("/diagram/layouts", name="create_diagram_layout")
async def create_diagram_layout(
    body: DiagramLayoutCreate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user_from_token(authorization, db)
    now = datetime.utcnow()
    layout = DiagramLayout(
        id=str(uuid.uuid4()),
        name=body.name,
        filters=json.dumps(body.filters or {}),
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return {
        "status": "success",
        "layout": {
            "id": layout.id,
            "name": layout.name,
            "filters": json.loads(layout.filters) if layout.filters else {},
            "created_at": layout.created_at.isoformat(),
            "updated_at": layout.updated_at.isoformat(),
        },
    }


@router.put("/diagram/layouts/{layout_id}", name="update_diagram_layout")
async def update_diagram_layout(
    layout_id: str,
    body: DiagramLayoutUpdate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user_from_token(authorization, db)
    result = await db.execute(
        select(DiagramLayout).where(
            DiagramLayout.id == layout_id, DiagramLayout.created_by == user.id
        )
    )
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    if body.name is not None:
        layout.name = body.name
    if body.filters is not None:
        layout.filters = json.dumps(body.filters)
    layout.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(layout)
    return {
        "status": "success",
        "layout": {
            "id": layout.id,
            "name": layout.name,
            "filters": json.loads(layout.filters) if layout.filters else {},
            "created_at": layout.created_at.isoformat(),
            "updated_at": layout.updated_at.isoformat(),
        },
    }


@router.delete("/diagram/layouts/{layout_id}", name="delete_diagram_layout")
async def delete_diagram_layout(
    layout_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user_from_token(authorization, db)
    result = await db.execute(
        select(DiagramLayout).where(
            DiagramLayout.id == layout_id, DiagramLayout.created_by == user.id
        )
    )
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    await db.delete(layout)
    await db.commit()
    return {"status": "success"}
