"""
User Activity Tracking API
===========================
Endpoints for tracking and retrieving user activity for personalized home page.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_authenticated_user
from app.infrastructure.database.repositories.user_activity_repository import UserActivityRepository

router = APIRouter(prefix="/user-activity", tags=["user-activity"])


@router.post("/track")
async def track_activity(
    activity_type: str = Body(...),
    entity_name: Optional[str] = Body(None),
    page_path: Optional[str] = Body(None),
    page_label: Optional[str] = Body(None),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Track a user activity.
    
    Args:
        activity_type: Type of activity (entity_view, page_visit, quick_create, admin_action)
        entity_name: Name of entity if applicable
        page_path: Route path if applicable
        page_label: Human-readable label for the page
    """
    valid_types = ["entity_view", "page_visit", "quick_create", "admin_action"]
    if activity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid activity_type. Must be one of: {valid_types}")
    
    repo = UserActivityRepository(db)
    activity = await repo.record_activity(
        user_id=current_user.id,
        username=current_user.username,
        activity_type=activity_type,
        entity_name=entity_name,
        page_path=page_path,
        page_label=page_label,
    )
    
    await db.commit()
    
    return {
        "status": "success",
        "data": {
            "id": activity.id,
            "visit_count": activity.visit_count,
            "score": activity.score,
        }
    }


@router.post("/batch")
async def track_activities_batch(
    body: dict = Body(...),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Track multiple user activities in a batch.
    
    Args:
        body: Dictionary containing activities list
    """
    activities = body.get("activities", [])
    valid_types = ["entity_view", "page_visit", "quick_create", "admin_action"]
    repo = UserActivityRepository(db)
    
    for activity_data in activities:
        activity_type = activity_data.get("activity_type")
        if activity_type not in valid_types:
            continue  # Skip invalid activity types
        
        await repo.record_activity(
            user_id=current_user.id,
            username=current_user.username,
            activity_type=activity_type,
            entity_name=activity_data.get("entity_name"),
            page_path=activity_data.get("page_path"),
            page_label=activity_data.get("page_label"),
        )
    
    await db.commit()
    
    return {
        "status": "success",
        "data": {
            "processed": len(activities),
        }
    }


@router.get("/frequent-entities")
async def get_frequent_entities(
    limit: int = Query(5, ge=1, le=20),
    days_ago: int = Query(30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's most frequently accessed entities.
    
    Returns ranked list of entities based on visit frequency and recency.
    """
    repo = UserActivityRepository(db)
    entities = await repo.get_frequent_entities(
        user_id=current_user.id,
        limit=limit,
        days_ago=days_ago,
    )
    
    return {
        "status": "success",
        "data": entities,
    }


@router.get("/frequent-pages")
async def get_frequent_pages(
    limit: int = Query(5, ge=1, le=20),
    days_ago: int = Query(30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's most frequently visited pages (non-entity pages).
    
    Returns ranked list of pages based on visit frequency and recency.
    """
    repo = UserActivityRepository(db)
    pages = await repo.get_frequent_pages(
        user_id=current_user.id,
        limit=limit,
        days_ago=days_ago,
    )
    
    return {
        "status": "success",
        "data": pages,
    }


@router.get("/all-activities")
async def get_all_activities(
    activity_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    days_ago: Optional[int] = Query(None, ge=1, le=365),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all user activities with optional filtering.
    
    Args:
        activity_type: Filter by activity type
        limit: Maximum number of results
        days_ago: Filter to activities from last N days
    """
    repo = UserActivityRepository(db)
    activities = await repo.get_user_activities(
        user_id=current_user.id,
        activity_type=activity_type,
        limit=limit,
        days_ago=days_ago,
    )
    
    return {
        "status": "success",
        "data": [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "entity_name": a.entity_name,
                "page_path": a.page_path,
                "page_label": a.page_label,
                "visit_count": a.visit_count,
                "score": a.score,
                "last_visited_at": a.last_visited_at.isoformat() if a.last_visited_at else None,
            }
            for a in activities
        ],
    }


@router.get("/recent-records")
async def get_recent_records(
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get latest records created by the user across all entities.
    
    Args:
        limit: Maximum number of results
    """
    from sqlalchemy import inspect, text
    from app.meta.registry import MetaRegistry
    
    # Get all entities from MetaRegistry
    entities = MetaRegistry.list_all()
    recent_records = []
    
    for meta in entities:
        entity_name = meta.name
        if meta.is_system:
            continue
            
        table_name = meta.table_name
        if not table_name:
            continue
            
        try:
            # Check if table has created_by and created_at columns
            inspector = inspect(db.bind.sync_engine)
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            
            if "created_by" not in columns or "created_at" not in columns:
                continue
            
            # Query for recent records created by user
            query = text(f"""
                SELECT 
                    '{entity_name}' as entity_name,
                    '{meta.label}' as entity_label,
                    id,
                    CASE 
                        WHEN title IS NOT NULL THEN title
                        WHEN name IS NOT NULL THEN name
                        ELSE id
                    END as record_title,
                    created_at
                FROM {table_name}
                WHERE created_by = :user_id
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            result = await db.execute(query, {"user_id": current_user.id})
            records = result.fetchall()
            
            for row in records:
                recent_records.append({
                    "entity_name": row.entity_name,
                    "entity_label": row.entity_label,
                    "record_id": row.id,
                    "record_title": row.record_title,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
        except Exception:
            # Skip tables that don't exist or have issues
            continue
    
    # Sort by created_at and limit
    recent_records.sort(key=lambda x: x["created_at"] or "", reverse=True)
    recent_records = recent_records[:limit]
    
    return {
        "status": "success",
        "data": recent_records,
    }


@router.get("/home-data")
async def get_home_data(
    entities_limit: int = Query(5, ge=1, le=20),
    pages_limit: int = Query(5, ge=1, le=20),
    records_limit: int = Query(10, ge=1, le=50),
    days_ago: int = Query(30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all home page data in a single batch call.
    
    Returns frequent entities, frequent pages, and recent records created by user.
    
    Args:
        entities_limit: Maximum number of frequent entities
        pages_limit: Maximum number of frequent pages
        records_limit: Maximum number of recent records
        days_ago: Filter activities from last N days
    """
    from sqlalchemy import inspect, text
    from app.meta.registry import MetaRegistry
    
    repo = UserActivityRepository(db)
    
    # Get all entities metadata once
    all_entities = MetaRegistry.list_all()
    
    # Get frequent entities
    entities = await repo.get_frequent_entities(
        user_id=current_user.id,
        limit=entities_limit,
        days_ago=days_ago,
    )
    
    # Get frequent pages
    pages = await repo.get_frequent_pages(
        user_id=current_user.id,
        limit=pages_limit,
        days_ago=days_ago,
    )
    
    # Fix page labels by looking up entity metadata
    for page in pages:
        # If page_label looks like a raw path, try to get proper label
        if page["page_label"] and page["page_label"].startswith("/"):
            path_parts = [p for p in page["page_path"].split("/") if p]
            if path_parts:
                entity_name = path_parts[0]
                # Find entity in metadata
                for meta in all_entities:
                    if meta.name == entity_name:
                        page["page_label"] = meta.label
                        break
    
    # Get recent records
    recent_records = []
    
    for meta in all_entities:
        entity_name = meta.name
        if meta.is_system:
            continue
            
        table_name = meta.table_name
        if not table_name:
            continue
            
        try:
            inspector = inspect(db.bind.sync_engine)
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            
            if "created_by" not in columns or "created_at" not in columns:
                continue
            
            query = text(f"""
                SELECT 
                    '{entity_name}' as entity_name,
                    '{meta.label}' as entity_label,
                    id,
                    CASE 
                        WHEN title IS NOT NULL THEN title
                        WHEN name IS NOT NULL THEN name
                        ELSE id
                    END as record_title,
                    created_at
                FROM {table_name}
                WHERE created_by = :user_id
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            result = await db.execute(query, {"user_id": current_user.id})
            records = result.fetchall()
            
            for row in records:
                recent_records.append({
                    "entity_name": row.entity_name,
                    "entity_label": row.entity_label,
                    "record_id": row.id,
                    "record_title": row.record_title,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
        except Exception:
            continue
    
    recent_records.sort(key=lambda x: x["created_at"] or "", reverse=True)
    recent_records = recent_records[:records_limit]
    
    # Get entity icons only for entities in the results
    entity_icons = {}
    needed_entities = set()
    
    # Add entities from frequent_entities
    for entity in entities:
        needed_entities.add(entity["entity_name"])
    
    # Add entities from frequent_pages (extract entity name from path)
    for page in pages:
        path_parts = [p for p in page["page_path"].split("/") if p]
        if path_parts:
            needed_entities.add(path_parts[0])
    
    # Add entities from recent_records
    for record in recent_records:
        needed_entities.add(record["entity_name"])
    
    # Get icons only for needed entities
    for meta in all_entities:
        if meta.name in needed_entities:
            entity_icons[meta.name] = f"i-lucide-{meta.icon}" if meta.icon else "i-lucide-file"
    
    return {
        "status": "success",
        "data": {
            "frequent_entities": entities,
            "frequent_pages": pages,
            "recent_records": recent_records,
            "entity_icons": entity_icons,
        }
    }
