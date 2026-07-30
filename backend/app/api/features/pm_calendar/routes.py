"""
Preventive Maintenance Calendar Feature
=========================================
Endpoints for managing PM tasks on a monthly calendar view.
Each task is a maintenance_request linked to a planned_maintenance_activity,
with a work_order_activity holding the assigned labor and time.
"""
from datetime import date, datetime, timedelta
from typing import Optional
import traceback
import logging
from fastapi import APIRouter, Depends, Header, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, extract, delete, func
from pydantic import BaseModel as PydanticBaseModel

from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.documents.link_title_service import get_record_display_name
from app.application.services.maintenance.constants import FREQUENCY_DAYS
from app.application.services.documents.link_title_service import build_link_titles_batch, inject_link_name_fields, build_link_titles_single
from app.meta.registry import MetaRegistry

router = APIRouter(tags=["pm-calendar"])

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

# ── Color mapping ─────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "Draft": "#94a3b8",            # slate
    "Pending Approval": "#f59e0b", # amber
    "Approved": "#3b82f6",         # blue
    "Release": "#8b5cf6",          # violet
    "Completed": "#22c55e",        # green
    "Scheduled": "#3b82f6",        # blue
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_id(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:05d}"


async def _next_id(db: AsyncSession, model, prefix: str) -> str:
    """Get next sequential ID for a given model/prefix."""
    result = await db.execute(
        select(func.count()).select_from(model)
    )
    count = result.scalar() or 0
    # Try incrementing until we find a free one
    for i in range(count + 1, count + 100):
        candidate = _generate_id(prefix, i)
        existing = await db.execute(select(model).where(model.id == candidate))
        if not existing.scalar_one_or_none():
            return candidate
    return _generate_id(prefix, count + 1)


async def _get_or_create_activity(db: AsyncSession, activity_name: str) -> str:
    """Get existing maintenance_activity by name or create new one. Returns id."""
    model = get_entity_model("maintenance_activity")
    result = await db.execute(
        select(model).where(model.activity_name == activity_name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    new_id = await _next_id(db, model, "MTACT")
    record = model(
        id=new_id,
        activity_name=activity_name,
        description=activity_name,
    )
    db.add(record)
    await db.flush()
    return new_id


async def _get_or_create_pma(
    db: AsyncSession,
    maintenance_activity_id: str,
    activity_name: str,
    maintenance_plan_id: Optional[str] = None,
) -> str:
    """Get or create planned_maintenance_activity for Calendar Based scheduling."""
    model = get_entity_model("planned_maintenance_activity")
    result = await db.execute(
        select(model).where(
            and_(
                model.maintenance_activity == maintenance_activity_id,
                model.maintenance_schedule == "Calendar Based",
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    new_id = await _next_id(db, model, "PMA")
    record = model(
        id=new_id,
        maintenance_activity=maintenance_activity_id,
        maintenance_activity_name=activity_name,
        maintenance_schedule="Calendar Based",
        maintenance_plan=maintenance_plan_id,
    )
    db.add(record)
    await db.flush()
    return new_id


def _build_task_response(mr_dict: dict, woa_dict: Optional[dict], activity_name: str, laborer_name: str, minimal: bool = False) -> dict:
    """Build a unified task response dict.
    
    Args:
        mr_dict: Maintenance request data
        woa_dict: Work order activity data
        activity_name: Activity name
        laborer_name: Laborer name
        minimal: If True, return only essential fields for list view (id, activity_name, workflow_state, due_date, start_time, color)
    """
    start_time = None
    if woa_dict and woa_dict.get("start_date"):
        sd = woa_dict["start_date"]
        if isinstance(sd, str) and "T" in sd:
            start_time = sd.split("T")[1][:5]
        elif isinstance(sd, datetime):
            start_time = sd.strftime("%H:%M")

    ws = mr_dict.get("workflow_state") or "Draft"
    
    if minimal:
        return {
            "id": mr_dict["id"],
            "activity_name": activity_name,
            "workflow_state": ws,
            "due_date": mr_dict.get("due_date"),
            "start_time": start_time or "08:00",
            "color": STATUS_COLORS.get(ws, "#94a3b8"),
        }
    
    return {
        "id": mr_dict["id"],
        "activity_name": activity_name,
        "workflow_state": ws,
        "due_date": mr_dict.get("due_date"),
        "start_time": start_time or "08:00",
        "laborer": laborer_name,
        "assigned_to": woa_dict.get("assigned_to") if woa_dict else None,
        "work_order_activity_id": woa_dict.get("id") if woa_dict else None,
        "planned_maintenance_activity": mr_dict.get("planned_maintenance_activity"),
        "site": mr_dict.get("site"),
        "department": mr_dict.get("department"),
        "notes": mr_dict.get("description"),
        "color": STATUS_COLORS.get(ws, "#94a3b8"),
    }


# ── GET TASKS ─────────────────────────────────────────────────────────────────

@router.get("/pm-calendar/tasks", name="pm_calendar_tasks")
async def get_tasks(
    year: int = Query(...),
    month: int = Query(...),
    site: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Fetch PM calendar tasks for a given month by computing upcoming maintenance from
    Maintenance Calendar and Maintenance Interval definitions (lookup-only, no record creation).
    
    Returns computed tasks with essential fields: id, activity_name, workflow_state, due_date, start_time, color.
    """
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        user = await get_current_user_from_token(authorization, db)

        # Get required models
        cal_model = get_entity_model("maintenance_calendar")
        interval_model = get_entity_model("maintenance_interval")
        plan_model = get_entity_model("maintenance_plan")
        pma_model = get_entity_model("planned_maintenance_activity")
        activity_model = get_entity_model("maintenance_activity")
        asset_model = get_entity_model("asset")
        asset_prop_model = get_entity_model("asset_property")
        property_model = get_entity_model("property")

        if not all([cal_model, interval_model, plan_model, pma_model, activity_model, asset_model, asset_prop_model, property_model]):
            return {"status": "error", "message": "Required models not found"}

        # Build date range for the requested month
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        tasks = []
        task_counter = 0

        # ── Process Maintenance Calendar Records ───────────────────────────────────
        # Only process calendars with property references configured (validated PMs)
        calendars = (await db.execute(
            select(cal_model).where(
                and_(
                    cal_model.frequency.isnot(None),
                    cal_model.last_maintenance_date_property.isnot(None)
                )
            )
        )).scalars().all()
        
        for cal in calendars:
            if not cal.planned_maintenance_activity or not cal.frequency:
                continue

            # Get PMA and activity info
            pma = (await db.execute(select(pma_model).where(pma_model.id == cal.planned_maintenance_activity))).scalar_one_or_none()
            if not pma or not pma.maintenance_plan:
                continue

            # Get maintenance plan and find matching assets
            plan = (await db.execute(select(plan_model).where(plan_model.id == pma.maintenance_plan))).scalar_one_or_none()
            if not plan or not plan.asset_class:
                continue

            # Build asset filters
            asset_conditions = [
                asset_model.asset_class == plan.asset_class,
            ]
            if site:
                asset_conditions.append(asset_model.site == site)
            if department:
                asset_conditions.append(asset_model.department == department)

            assets = (await db.execute(select(asset_model).where(and_(*asset_conditions)))).scalars().all()

            for asset in assets:
                # Get last maintenance date from property
                last_date = None
                if cal.last_maintenance_date_property:
                    last_prop = (await db.execute(
                        select(asset_prop_model).where(
                            and_(
                                asset_prop_model.asset == asset.id,
                                asset_prop_model.property == cal.last_maintenance_date_property
                            )
                        )
                    )).scalar_one_or_none()
                    if last_prop and last_prop.property_value:
                        try:
                            last_date = date.fromisoformat(str(last_prop.property_value)[:10])
                        except Exception:
                            # Skip assets with invalid date format (not validated)
                            continue
                    else:
                        # Skip assets without property value (not validated)
                        continue
                else:
                    # Skip assets if property reference is missing (shouldn't happen due to filter above)
                    continue

                # Compute next due date based on frequency
                base_date = last_date  # No fallback - only validated assets
                frequency_days = FREQUENCY_DAYS.get(cal.frequency)
                if not frequency_days:
                    continue

                # Calculate next due date (add lead time if specified)
                lead_days = getattr(cal, "lead_calendar_days", 7) or 7
                try:
                    lead_days = int(lead_days)
                except (TypeError, ValueError):
                    lead_days = 7

                # Compute multiple upcoming dates within the month
                next_due = base_date
                while next_due <= last_day + timedelta(days=lead_days):
                    next_due = next_due + timedelta(days=frequency_days)
                    due_date_with_lead = next_due - timedelta(days=lead_days)
                    
                    # Check if this due date falls within the requested month
                    if first_day <= due_date_with_lead <= last_day:
                        task_counter += 1
                        task_id = f"PM-CAL-{task_counter:05d}"
                        asset_tag = getattr(asset, "asset_tag", None)
                        asset_display_name = asset_tag or getattr(asset, "description", asset.id) or asset.id
                        asset_workflow_state = getattr(asset, "workflow_state", None) or "Unknown"
                        tasks.append({
                            "id": task_id,
                            "activity_name": getattr(plan, "description", plan.id) or plan.id,
                            "workflow_state": "Scheduled",
                            "asset_workflow_state": asset_workflow_state,
                            "due_date": due_date_with_lead.isoformat(),
                            "start_time": "08:00",
                            "color": STATUS_COLORS.get("Scheduled", "#3b82f6"),
                            "plan_id": plan.id,
                            "asset_id": asset.id,
                            "asset_display_name": asset_display_name,
                            "planned_maintenance_activity": cal.planned_maintenance_activity,
                        })

        # ── Process Maintenance Interval Records ───────────────────────────────────
        # Only process intervals with property references configured (validated PMs)
        intervals = (await db.execute(
            select(interval_model).where(
                and_(
                    interval_model.interval.isnot(None),
                    interval_model.running_interval_property.isnot(None),
                    interval_model.last_interval_property.isnot(None)
                )
            )
        )).scalars().all()
        
        for interval_record in intervals:
            if not interval_record.planned_maintenance_activity or not interval_record.interval:
                continue

            # Get PMA and activity info
            pma = (await db.execute(select(pma_model).where(pma_model.id == interval_record.planned_maintenance_activity))).scalar_one_or_none()
            if not pma or not pma.maintenance_plan:
                continue

            # Get maintenance plan and find matching assets
            plan = (await db.execute(select(plan_model).where(plan_model.id == pma.maintenance_plan))).scalar_one_or_none()
            if not plan or not plan.asset_class:
                continue

            # Build asset filters
            asset_conditions = [
                asset_model.asset_class == plan.asset_class,
            ]
            if site:
                asset_conditions.append(asset_model.site == site)
            if department:
                asset_conditions.append(asset_model.department == department)

            assets = (await db.execute(select(asset_model).where(and_(*asset_conditions)))).scalars().all()

            for asset in assets:
                # Get running and last interval properties
                if not interval_record.running_interval_property or not interval_record.last_interval_property:
                    continue

                running_prop = (await db.execute(
                    select(asset_prop_model).where(
                        and_(
                            asset_prop_model.asset == asset.id,
                            asset_prop_model.property == interval_record.running_interval_property
                        )
                    )
                )).scalar_one_or_none()
                
                last_prop = (await db.execute(
                    select(asset_prop_model).where(
                        and_(
                            asset_prop_model.asset == asset.id,
                            asset_prop_model.property == interval_record.last_interval_property
                        )
                    )
                )).scalar_one_or_none()

                if not running_prop or not last_prop:
                    continue

                # Skip assets without valid property values (not validated)
                if not running_prop.property_value or not last_prop.property_value:
                    continue

                try:
                    running_value = float(running_prop.property_value)
                    last_value = float(last_prop.property_value)
                except Exception:
                    # Skip assets with invalid numeric format (not validated)
                    continue

                running_interval = running_value - last_value
                try:
                    interval_threshold = float(interval_record.interval or 0)
                    lead_interval = float(interval_record.lead_interval or 0)
                except Exception:
                    continue

                # Check if interval threshold is approaching
                if running_interval >= (interval_threshold - lead_interval):
                    task_counter += 1
                    task_id = f"PM-INT-{task_counter:05d}"
                    asset_tag = getattr(asset, "asset_tag", None)
                    asset_display_name = asset_tag or getattr(asset, "description", asset.id) or asset.id
                    asset_workflow_state = getattr(asset, "workflow_state", None) or "Unknown"
                    tasks.append({
                        "id": task_id,
                        "activity_name": getattr(plan, "description", plan.id) or plan.id,
                        "workflow_state": "Scheduled",
                        "asset_workflow_state": asset_workflow_state,
                        "due_date": first_day.isoformat(),  # Show at start of month for interval-based
                        "start_time": "08:00",
                        "color": STATUS_COLORS.get("Scheduled", "#3b82f6"),
                        "plan_id": plan.id,
                        "asset_id": asset.id,
                        "asset_display_name": asset_display_name,
                        "planned_maintenance_activity": interval_record.planned_maintenance_activity,
                    })

        # Sort tasks by due date
        tasks.sort(key=lambda x: x.get("due_date", ""))

        return {"status": "success", "data": tasks}
    
    except Exception as e:
        logger.error(f"Error in get_tasks: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": f"Error: {str(e)}"}


# ── GET PLAN ACTIVITIES ────────────────────────────────────────────────────────

@router.get("/pm-calendar/plan/{plan_id}/activities", name="pm_calendar_plan_activities")
async def get_plan_activities(
    plan_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all planned maintenance activities for a given maintenance plan."""
    logger = logging.getLogger(__name__)

    try:
        user = await get_current_user_from_token(authorization, db)

        pma_model = get_entity_model("planned_maintenance_activity")
        activity_model = get_entity_model("maintenance_activity")
        cal_model = get_entity_model("maintenance_calendar")
        interval_model = get_entity_model("maintenance_interval")
        plan_model = get_entity_model("maintenance_plan")
        interval_meta = MetaRegistry.get("maintenance_interval")

        if not pma_model:
            return {"status": "error", "message": "planned_maintenance_activity model not found"}
        if not cal_model:
            return {"status": "error", "message": "maintenance_calendar model not found"}
        if not interval_model:
            return {"status": "error", "message": "maintenance_interval model not found"}

        # Get plan display name
        plan_name = plan_id
        if plan_model:
            plan = (await db.execute(
                select(plan_model).where(plan_model.id == plan_id)
            )).scalar_one_or_none()
            if plan:
                plan_name = getattr(plan, "description", plan_id) or plan_id

        # Get all PMAs for the plan
        pmas = (await db.execute(
            select(pma_model).where(pma_model.maintenance_plan == plan_id)
        )).scalars().all()

        activities = []
        for pma in pmas:
            # Get maintenance activity details
            activity = None
            pma_activity_id = getattr(pma, "maintenance_activity", None)
            if pma_activity_id:
                activity = (await db.execute(
                    select(activity_model).where(activity_model.id == pma_activity_id)
                )).scalar_one_or_none()

            # Get scheduling info (calendar or interval)
            calendar = None
            interval_val = None

            pma_id = getattr(pma, "id", None)
            if pma_id:
                calendar = (await db.execute(
                    select(cal_model).where(cal_model.planned_maintenance_activity == pma_id)
                )).scalar_one_or_none()

                interval_val = (await db.execute(
                    select(interval_model).where(interval_model.planned_maintenance_activity == pma_id)
                )).scalar_one_or_none()

            # Determine scheduling type
            if calendar:
                scheduling_type = "calendar"
            elif interval_val:
                scheduling_type = "interval"
            else:
                scheduling_type = "none"

            # Resolve interval_unit_of_measure display name if it's a link field
            interval_unit_of_measure_name = None
            interval_unit_of_measure = getattr(interval_val, "interval_unit_of_measure", None) if interval_val else None
            if interval_val and interval_meta:
                interval_dict = record_to_dict(interval_val)
                link_titles = await build_link_titles_single(db, interval_meta, interval_dict)
                inject_link_name_fields(interval_meta, interval_dict, link_titles)
                interval_unit_of_measure_name = interval_dict.get("interval_unit_of_measure_name")

            activity_data = {
                "id": pma_id,
                "activity_name": activity.activity_name if activity else (getattr(pma, "maintenance_activity_name", None) or "Unknown Activity"),
                "scheduling_type": scheduling_type,
                "frequency": getattr(calendar, "frequency", None) if calendar else None,
                "interval": getattr(interval_val, "interval", None) if interval_val else None,
                "interval_unit_of_measure_name": interval_unit_of_measure_name or interval_unit_of_measure,
            }
            activities.append(activity_data)

        return {"status": "success", "data": activities, "plan_name": plan_name}

    except Exception as e:
        logger.error(f"Error in get_plan_activities: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": f"Error: {str(e)}"}


# ── COMPREHENSIVE ASSET PROPERTY VALIDATION ─────────────────────────────────────

@router.get("/pm-calendar/validate-asset-properties", name="pm_calendar_validate_asset_properties")
async def validate_asset_maintenance_properties(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Check all assets for missing or incorrect maintenance properties.
    
    Validates both calendar-based (last_maintenance_date_property) and 
    interval-based (running_interval_property, last_interval_property) 
    maintenance property requirements for assets.
    
    Returns a structured list showing:
    - Which asset classes require which properties
    - Which assets are missing those properties
    - Issues with property values (missing, invalid format, etc.)
    """
    logger = logging.getLogger(__name__)
    
    try:
        user = await get_current_user_from_token(authorization, db)

        # Get required models
        cal_model = get_entity_model("maintenance_calendar")
        interval_model = get_entity_model("maintenance_interval")
        plan_model = get_entity_model("maintenance_plan")
        pma_model = get_entity_model("planned_maintenance_activity")
        asset_model = get_entity_model("asset")
        asset_class_model = get_entity_model("asset_class")
        asset_prop_model = get_entity_model("asset_property")
        property_model = get_entity_model("property")

        if not all([cal_model, interval_model, plan_model, pma_model, asset_model, asset_class_model, asset_prop_model, property_model]):
            return {"status": "error", "message": "Required models not found"}

        # Build a map of asset_class -> required properties
        # Structure: {asset_class_id: {"calendar": [prop_ids], "interval": [prop_ids]}}
        asset_class_requirements = {}
        
        # Track configuration issues (missing property references)
        configuration_issues = []

        # Process calendar-based requirements
        all_calendars = (await db.execute(
            select(cal_model)
        )).scalars().all()

        for cal in all_calendars:
            if not cal.planned_maintenance_activity:
                continue

            pma = (await db.execute(
                select(pma_model).where(pma_model.id == cal.planned_maintenance_activity)
            )).scalar_one_or_none()
            if not pma or not pma.maintenance_plan:
                continue

            plan = (await db.execute(
                select(plan_model).where(plan_model.id == pma.maintenance_plan)
            )).scalar_one_or_none()
            if not plan:
                continue
            if not plan.asset_class:
                # Track configuration issue - maintenance plan missing asset_class
                configuration_issues.append({
                    "type": "calendar",
                    "maintenance_calendar_id": cal.id,
                    "maintenance_calendar_display_name": getattr(pma, "description", pma.id) or pma.id,
                    "maintenance_plan_id": plan.id,
                    "maintenance_plan_name": getattr(plan, "description", plan.id) or plan.id,
                    "asset_class_id": None,
                    "asset_class_display_name": None,
                    "issue": "Maintenance Plan does not have an asset_class assigned"
                })
                continue

            # Check if property reference is configured
            if not cal.last_maintenance_date_property:
                # Get display names manually
                asset_class_record = (await db.execute(
                    select(asset_class_model).where(asset_class_model.id == plan.asset_class)
                )).scalar_one_or_none()
                asset_class_name = getattr(asset_class_record, "name", None) if asset_class_record else None
                asset_class_display_name = asset_class_name or getattr(asset_class_record, "description", plan.asset_class) if asset_class_record else plan.asset_class
                plan_name = getattr(plan, "description", plan.id) or plan.id
                
                # Track configuration issue
                configuration_issues.append({
                    "type": "calendar",
                    "maintenance_calendar_id": cal.id,
                    "maintenance_calendar_display_name": plan_name,  # Use plan name instead of calendar ID
                    "maintenance_plan_id": plan.id,
                    "maintenance_plan_name": plan_name,
                    "asset_class_id": plan.asset_class,
                    "asset_class_display_name": asset_class_display_name,
                    "issue": "Last Maintenance Date property not configured"
                })
                continue

            if plan.asset_class not in asset_class_requirements:
                asset_class_requirements[plan.asset_class] = {"calendar": [], "interval": []}
            
            if cal.last_maintenance_date_property not in asset_class_requirements[plan.asset_class]["calendar"]:
                asset_class_requirements[plan.asset_class]["calendar"].append(cal.last_maintenance_date_property)

        # Process interval-based requirements
        all_intervals = (await db.execute(
            select(interval_model)
        )).scalars().all()

        for interval in all_intervals:
            if not interval.planned_maintenance_activity:
                continue

            pma = (await db.execute(
                select(pma_model).where(pma_model.id == interval.planned_maintenance_activity)
            )).scalar_one_or_none()
            if not pma or not pma.maintenance_plan:
                continue

            plan = (await db.execute(
                select(plan_model).where(plan_model.id == pma.maintenance_plan)
            )).scalar_one_or_none()
            if not plan:
                continue
            if not plan.asset_class:
                # Track configuration issue - maintenance plan missing asset_class
                configuration_issues.append({
                    "type": "interval",
                    "maintenance_interval_id": interval.id,
                    "maintenance_interval_display_name": getattr(pma, "description", pma.id) or pma.id,
                    "maintenance_plan_id": plan.id,
                    "maintenance_plan_name": getattr(plan, "description", plan.id) or plan.id,
                    "asset_class_id": None,
                    "asset_class_display_name": None,
                    "issue": "Maintenance Plan does not have an asset_class assigned"
                })
                continue

            # Check if property references are configured
            if not interval.running_interval_property or not interval.last_interval_property:
                # Get display names manually
                asset_class_record = (await db.execute(
                    select(asset_class_model).where(asset_class_model.id == plan.asset_class)
                )).scalar_one_or_none()
                asset_class_name = getattr(asset_class_record, "name", None) if asset_class_record else None
                asset_class_display_name = asset_class_name or getattr(asset_class_record, "description", plan.asset_class) if asset_class_record else plan.asset_class
                plan_name = getattr(plan, "description", plan.id) or plan.id
                
                # Track configuration issue
                configuration_issues.append({
                    "type": "interval",
                    "maintenance_interval_id": interval.id,
                    "maintenance_interval_display_name": plan_name,  # Use plan name instead of interval ID
                    "maintenance_plan_id": plan.id,
                    "maintenance_plan_name": plan_name,
                    "asset_class_id": plan.asset_class,
                    "asset_class_display_name": asset_class_display_name,
                    "issue": "Running Interval or Last Interval property not configured"
                })
                continue

            if plan.asset_class not in asset_class_requirements:
                asset_class_requirements[plan.asset_class] = {"calendar": [], "interval": []}
            
            if interval.running_interval_property and interval.running_interval_property not in asset_class_requirements[plan.asset_class]["interval"]:
                asset_class_requirements[plan.asset_class]["interval"].append(interval.running_interval_property)
            
            if interval.last_interval_property and interval.last_interval_property not in asset_class_requirements[plan.asset_class]["interval"]:
                asset_class_requirements[plan.asset_class]["interval"].append(interval.last_interval_property)

        # Validate assets against requirements and build unified issues list
        unified_issues = []
        
        # Add configuration issues first
        for config_issue in configuration_issues:
            unified_issues.append({
                "issue_type": "configuration",
                "type": config_issue["type"],
                "maintenance_plan_id": config_issue["maintenance_plan_id"],
                "maintenance_plan_name": config_issue["maintenance_plan_name"],
                "issue": config_issue["issue"]
            })

        # Add asset validation issues
        for asset_class_id, requirements in asset_class_requirements.items():
            # Get asset class name
            asset_class_record = (await db.execute(
                select(asset_class_model).where(asset_class_model.id == asset_class_id)
            )).scalar_one_or_none()
            asset_class_name = getattr(asset_class_record, "name", None) if asset_class_record else None
            asset_class_display_name = asset_class_name or getattr(asset_class_record, "description", asset_class_id) if asset_class_record else asset_class_id

            # Get property details
            property_details = {}
            all_props = set(requirements["calendar"] + requirements["interval"])
            for prop_id in all_props:
                prop_record = (await db.execute(
                    select(property_model).where(property_model.id == prop_id)
                )).scalar_one_or_none()
                if prop_record:
                    prop_name = getattr(prop_record, "name", prop_id)
                    prop_type = "calendar" if prop_id in requirements["calendar"] else "interval"
                    property_details[prop_id] = {
                        "property_name": prop_name,
                        "type": prop_type
                    }

            # Get all active assets for this asset class
            assets = (await db.execute(
                select(asset_model).where(
                    and_(
                        asset_model.asset_class == asset_class_id,
                        asset_model.workflow_state == "active"
                    )
                )
            )).scalars().all()

            for asset in assets:
                asset_issues = []

                # Check calendar properties
                for prop_id in requirements["calendar"]:
                    asset_prop = (await db.execute(
                        select(asset_prop_model).where(
                            and_(
                                asset_prop_model.asset == asset.id,
                                asset_prop_model.property == prop_id
                            )
                        )
                    )).scalar_one_or_none()

                    prop_name = property_details[prop_id]["property_name"]
                    
                    if not asset_prop:
                        asset_issues.append({
                            "property_id": prop_id,
                            "property_name": prop_name,
                            "type": "calendar",
                            "issue": f"{prop_name} property not set"
                        })
                    elif not asset_prop.property_value:
                        asset_issues.append({
                            "property_id": prop_id,
                            "property_name": prop_name,
                            "type": "calendar",
                            "issue": f"{prop_name} property value is blank"
                        })
                    else:
                        # Validate date format
                        try:
                            date_str = str(asset_prop.property_value)[:10]
                            date.fromisoformat(date_str)
                        except Exception:
                            asset_issues.append({
                                "property_id": prop_id,
                                "property_name": prop_name,
                                "type": "calendar",
                                "issue": f"{prop_name} property has invalid date format (expected YYYY-MM-DD)"
                            })

                # Check interval properties
                for prop_id in requirements["interval"]:
                    asset_prop = (await db.execute(
                        select(asset_prop_model).where(
                            and_(
                                asset_prop_model.asset == asset.id,
                                asset_prop_model.property == prop_id
                            )
                        )
                    )).scalar_one_or_none()

                    prop_name = property_details[prop_id]["property_name"]
                    
                    if not asset_prop:
                        asset_issues.append({
                            "property_id": prop_id,
                            "property_name": prop_name,
                            "type": "interval",
                            "issue": f"{prop_name} property not set"
                        })
                    elif not asset_prop.property_value:
                        asset_issues.append({
                            "property_id": prop_id,
                            "property_name": prop_name,
                            "type": "interval",
                            "issue": f"{prop_name} property value is blank"
                        })
                    else:
                        # Validate numeric format
                        try:
                            float(asset_prop.property_value)
                        except Exception:
                            asset_issues.append({
                                "property_id": prop_id,
                                "property_name": prop_name,
                                "type": "interval",
                                "issue": f"{prop_name} property has invalid numeric format"
                            })

                # Add asset issues to unified list
                for asset_issue in asset_issues:
                    # Get asset display name from asset_tag field
                    asset_tag = getattr(asset, "asset_tag", None)
                    asset_display_name = asset_tag or getattr(asset, "description", asset.id) or asset.id
                    
                    unified_issues.append({
                        "issue_type": "asset",
                        "asset_id": asset.id,
                        "asset_display_name": asset_display_name,
                        "issue": asset_issue["issue"]
                    })

        # Sort results - configuration issues first, then asset issues
        unified_issues.sort(key=lambda x: (0 if x["issue_type"] == "configuration" else 1, x.get("asset_display_name", x.get("maintenance_plan_name", ""))))

        config_count = len([i for i in unified_issues if i["issue_type"] == "configuration"])
        asset_count = len([i for i in unified_issues if i["issue_type"] == "asset"])
        
        message_parts = []
        if config_count > 0:
            message_parts.append(f"{config_count} configuration issues (missing property references)")
        if asset_count > 0:
            message_parts.append(f"{asset_count} assets needing property updates")
        
        if not message_parts:
            message = "No issues found - all property references are configured and assets have required properties"
        else:
            message = "Found " + ", ".join(message_parts)

        return {
            "status": "success",
            "data": {
                "issues": unified_issues
            },
            "message": message
        }

    except Exception as e:
        logger.error(f"Error in validate_asset_maintenance_properties: {str(e)}\n{traceback.format_exc()}")
        return {"status": "error", "message": f"Error: {str(e)}"}
