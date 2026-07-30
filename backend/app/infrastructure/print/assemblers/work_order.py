"""
Work Order Print Data Assembler
================================
Gathers Work Order header + activities + labor/parts/equipment details for the WO print template.
"""
from typing import Any, Dict, List
import asyncio
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document_service import DocumentAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.application.services.documents.print_resolver import (
    resolve_link_display,
    resolve_many_link_displays,
)
from app.application.services.documents.print_formatters import (
    format_workflow_state,
    get_priority_description,
    format_date,
    format_datetime,
)




class WorkOrderAssembler:
    """Assembles print context for work_order entity."""

    entity_name = "work_order"

    def get_template_name(self) -> str:
        return "work_order.html"

    async def assemble(self, record: dict, db: AsyncSession) -> dict[str, Any]:
        wo_id = record.get("id", "")

        # Create document service
        document_repo = DocumentRepository(db)
        document_service = DocumentAppService(document_repo)

        # Fetch work order activities
        activities = await document_service.get_list(
            "work_order_activity",
            filters={"work_order": wo_id},
            order_by="start_date",
        )

        # Resolve link displays for header
        site_name = await resolve_link_display("site", record.get("site"), db)
        dept_name = await resolve_link_display("department", record.get("department"), db)
        cost_code_name = await resolve_link_display("cost_code", record.get("cost_code"), db)

        # Format priority with description
        priority = record.get("priority", "")
        priority_desc = get_priority_description(priority)
        priority_with_desc = f"{priority} - {priority_desc}" if priority_desc else priority

        # Build activity details with labor, parts, and equipment
        activity_details = []
        for activity in activities:
            activity_id = activity.get("id")
            
            # Fetch related records for this activity
            [labor_records, parts_records, equipment_records] = await asyncio.gather(
                document_service.get_list("work_order_labor", filters={"work_order_activity": activity_id}, order_by="start_datetime"),
                document_service.get_list("work_order_parts", filters={"work_order_activity": activity_id}, order_by="date_required"),
                document_service.get_list("work_order_equipment", filters={"work_order_activity": activity_id}, order_by="start_datetime"),
                return_exceptions=True,
            )

            # Handle exceptions
            labor_records = [] if isinstance(labor_records, Exception) else labor_records
            parts_records = [] if isinstance(parts_records, Exception) else parts_records
            equipment_records = [] if isinstance(equipment_records, Exception) else equipment_records

            # Resolve link displays for activity
            asset_name = await resolve_link_display("asset", activity.get("work_item"), db)
            position_name = await resolve_link_display("position", activity.get("position"), db)
            assigned_to_name = await resolve_link_display("labor", activity.get("assigned_to"), db)
            location_name = await resolve_link_display("location", activity.get("location"), db)
            activity_site_name = await resolve_link_display("site", activity.get("site"), db)
            activity_dept_name = await resolve_link_display("department", activity.get("department"), db)

            # Resolve labor displays
            labor_ids = [str(l.get("labor")) for l in labor_records if l.get("labor")]
            trade_ids = [str(l.get("trade")) for l in labor_records if l.get("trade")]
            labor_display = await resolve_many_link_displays("labor", labor_ids, db)
            trade_display = await resolve_many_link_displays("trade", trade_ids, db)

            # Resolve parts displays
            part_ids = [str(p.get("item")) for p in parts_records if p.get("item")]
            uom_ids = [str(p.get("unit_of_measure")) for p in parts_records if p.get("unit_of_measure")]
            part_display = await resolve_many_link_displays("item", part_ids, db)
            uom_display = await resolve_many_link_displays("unit_of_measure", uom_ids, db)

            # Resolve equipment displays
            equip_ids = [str(e.get("equipment")) for e in equipment_records if e.get("equipment")]
            equip_item_ids = [str(e.get("item")) for e in equipment_records if e.get("item")]
            equipment_display = await resolve_many_link_displays("equipment", equip_ids, db)
            equip_item_display = await resolve_many_link_displays("item", equip_item_ids, db)

            # Build labor details
            labor_details = []
            total_labor_hours = 0.0
            for labor in labor_records:
                hours = labor.get("total_hours_used") or 0.0
                total_labor_hours += hours
                labor_id = labor.get("labor")
                trade_id = labor.get("trade")
                
                labor_details.append({
                    "trade": trade_display.get(str(trade_id), ""),
                    "laborer": labor_display.get(str(labor_id), ""),
                    "lead": "Yes" if labor.get("lead") else "No",
                    "start": format_datetime(labor.get("start_datetime")),
                    "end": format_datetime(labor.get("end_datetime")),
                    "hours": f"{hours:.2f}",
                })

            # Build parts details
            parts_details = []
            for part in parts_records:
                item_id = part.get("item")
                uom_id = part.get("unit_of_measure")
                
                parts_details.append({
                    "item": part_display.get(str(item_id), ""),
                    "uom": uom_display.get(str(uom_id), ""),
                    "date_required": format_date(part.get("date_required")),
                    "qty_required": part.get("quantity_required") or 0,
                    "qty_issued": part.get("quantity_issued") or 0,
                    "qty_returned": part.get("quantity_returned") or 0,
                    "actual_qty": part.get("total_actual_qty") or 0,
                    "avail_qty": part.get("total_avail_qty") or 0,
                })

            # Build equipment details
            equipment_details = []
            total_equipment_hours = 0.0
            for equipment in equipment_records:
                hours = equipment.get("total_hours_used") or 0.0
                total_equipment_hours += hours
                equip_id = equipment.get("equipment")
                item_id = equipment.get("item")
                
                equipment_details.append({
                    "equipment": equipment_display.get(str(equip_id), ""),
                    "item": equip_item_display.get(str(item_id), ""),
                    "start": format_datetime(equipment.get("start_datetime")),
                    "end": format_datetime(equipment.get("end_datetime")),
                    "hours": f"{hours:.2f}",
                    "est_hours": f"{equipment.get('estimated_hours') or 0:.2f}",
                })

            activity_details.append({
                "id": activity_id,
                "description": activity.get("description", ""),
                "activity_type": activity.get("activity_type_name", ""),
                "work_item_type": activity.get("work_item_type", ""),
                "asset": asset_name,
                "position": position_name,
                "assigned_to": assigned_to_name,
                "location": location_name,
                "site": activity_site_name or site_name,
                "department": activity_dept_name or dept_name,
                "start_date": format_datetime(activity.get("start_date")),
                "end_date": format_datetime(activity.get("end_date")),
                "workflow_state": format_workflow_state(activity.get("workflow_state", "")),
                "needs_repair": "Yes" if activity.get("does_it_need_repair") else "No",
                "labor": labor_details,
                "parts": parts_details,
                "equipment": equipment_details,
                "total_labor_hours": f"{total_labor_hours:.2f}",
                "total_equipment_hours": f"{total_equipment_hours:.2f}",
                "labor_count": len(labor_details),
                "parts_count": len(parts_details),
                "equipment_count": len(equipment_details),
            })

        # Calculate totals across all activities
        total_activities = len(activity_details)
        total_labor_all = sum(float(a["total_labor_hours"]) for a in activity_details)
        total_equipment_all = sum(float(a["total_equipment_hours"]) for a in activity_details)
        total_parts_all = sum(a["parts_count"] for a in activity_details)

        return {
            "work_order": {
                "id": wo_id,
                "type": record.get("work_order_type", ""),
                "description": record.get("description", ""),
                "priority": priority,
                "priority_with_description": priority_with_desc,
                "severity": record.get("severity", ""),
                "due_date": format_date(record.get("due_date")),
                "workflow_state": format_workflow_state(record.get("workflow_state", "")),
                "site": site_name,
                "department": dept_name,
                "cost_code": cost_code_name,
                "incident": await resolve_link_display("incident", record.get("incident"), db),
                "category_of_failure": await resolve_link_display("category_of_failure", record.get("category_of_failure"), db),
            },
            "activities": activity_details,
            "summary": {
                "total_activities": total_activities,
                "total_labor_hours": f"{total_labor_all:.2f}",
                "total_equipment_hours": f"{total_equipment_all:.2f}",
                "total_parts_items": total_parts_all,
            },
            "branding": {
                "organization_name": "Organization",
                "description": "",
                "logo_url": None,
            },
        }


