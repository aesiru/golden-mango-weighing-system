"""
Purchase Request Print Data Assembler
======================================
Gathers PR header + line items + requestor info for the PR print template.
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


class PurchaseRequestAssembler:
    """Assembles print context for purchase_request entity."""

    entity_name = "purchase_request"

    def get_template_name(self) -> str:
        return "purchase_request.html"

    async def assemble(self, record: dict, db: AsyncSession) -> dict[str, Any]:
        pr_id = record.get("id", "")

        # Create document service
        document_repo = DocumentRepository(db)
        document_service = DocumentAppService(document_repo)

        # Fetch line items
        lines = await document_service.get_list(
            "purchase_request_line",
            filters={"purchase_request": pr_id},
            order_by="line_row_num",
        )

        site_data: dict[str, Any] = {}
        site_id = record.get("site")
        if site_id:
            site_doc = await document_service.get_doc("site", site_id, as_dict=True)
            if site_doc:
                site_data = site_doc

        # Resolve department / requestor display values
        dept_name = await resolve_link_display("department", record.get("department"), db)

        requestor_name = record.get("requestor_name", "")
        if not requestor_name:
            requestor_name = await resolve_link_display("employee", record.get("requestor"), db)

        # Batch-resolve common detail link fields from lines
        item_ids = [str(l.get("item")) for l in lines if l.get("item")]
        uom_ids = [str(l.get("unit_of_measure")) for l in lines if l.get("unit_of_measure")]
        vendor_ids = [str(l.get("vendor")) for l in lines if l.get("vendor")]

        item_display = await resolve_many_link_displays("item", item_ids, db)
        uom_display = await resolve_many_link_displays("unit_of_measure", uom_ids, db)
        vendor_display = await resolve_many_link_displays("vendor", vendor_ids, db)

        supplier_name = ""
        for vid in vendor_ids:
            supplier_name = vendor_display.get(vid, "")
            if supplier_name:
                break

        # Build line items for template
        line_items = []
        for line in lines:
            qty = line.get("qty_required") or 0
            unit_cost = line.get("unit_cost") or 0.0
            total = line.get("total_line_amount") or (qty * unit_cost)

            # Resolve UoM label (title_field)
            uom_id = line.get("unit_of_measure")
            uom_label = "pc"
            if uom_id:
                uom_label = uom_display.get(str(uom_id), str(uom_id))

            # Resolve item label (title_field) for use when description is missing
            item_label = ""
            item_id = line.get("item")
            if item_id:
                item_label = item_display.get(str(item_id), str(item_id))

            line_items.append({
                "item_id": str(item_id) if item_id else "",
                "item_name": item_label,
                "description": line.get("item_description") or item_label or "",
                "qty": qty,
                "unit": uom_label,
                "unit_price": f"{unit_cost:,.2f}" if unit_cost else "",
                "total": f"{total:,.2f}" if total else "0.00",
            })

        return {
            "pr_number": pr_id,
            "pr_date": _format_date(record.get("date_requested")),
            # Company info
            "company_address": site_data.get("address", ""),
            "company_contact": site_data.get("contact_number", ""),
            # Meta
            "requesting_department": dept_name,
            "purpose": record.get("pr_description", ""),
            "supplier_name": supplier_name,
            "requestor_name": requestor_name,
            # Line items
            "line_items": line_items,
            # Approval
            "approved_po_number": "",
        }


def _format_date(val: Any) -> str:
    """Format a date value to string."""
    if val is None:
        return ""
    if isinstance(val, (date, datetime)):
        return val.strftime("%B %d, %Y")
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val).strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return val
    return str(val)
