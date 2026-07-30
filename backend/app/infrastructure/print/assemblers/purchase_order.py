"""
Purchase Order Print Data Assembler
====================================
Gathers PO header + line items + vendor info for the PO print template.
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


class PurchaseOrderAssembler:
    """Assembles print context for purchase_order entity."""

    entity_name = "purchase_order"

    def get_template_name(self) -> str:
        return "purchase_order.html"

    async def assemble(self, record: dict, db: AsyncSession) -> dict[str, Any]:
        po_id = record.get("id", "")

        # Create document service
        document_repo = DocumentRepository(db)
        document_service = DocumentAppService(document_repo)

        # Fetch line items
        lines = await document_service.get_list(
            "purchase_order_line",
            filters={"po_id": po_id},
            order_by="line_row_num",
        )

        # Resolve header-detail link displays using each entity's title_field
        vendor_id = record.get("vendor")
        vendor_name = await resolve_link_display("vendor", vendor_id, db)

        vendor_data: dict[str, Any] = {}
        if vendor_id:
            vendor_doc = await document_service.get_doc("vendor", vendor_id, as_dict=True)
            if vendor_doc:
                vendor_data = vendor_doc

        site_data: dict[str, Any] = {}
        site_id = record.get("site")
        if site_id:
            site_doc = await document_service.get_doc("site", site_id, as_dict=True)
            if site_doc:
                site_data = site_doc

        site_name = await resolve_link_display("site", site_id, db)
        dept_name = await resolve_link_display("department", record.get("department"), db)

        # Batch-resolve item display values (title_field)
        item_ids = [str(l.get("item_id")) for l in lines if l.get("item_id")]
        item_display = await resolve_many_link_displays("item", item_ids, db)

        # Resolve unit of measure via Item.uom (if available)
        item_docs = await asyncio.gather(
            *[document_service.get_doc("item", iid, as_dict=True) for iid in sorted({i for i in item_ids if i})],
            return_exceptions=True,
        )
        item_to_uom: dict[str, str] = {}
        uom_ids: list[str] = []
        for iid, doc in zip(sorted({i for i in item_ids if i}), item_docs):
            if isinstance(doc, Exception) or not doc:
                continue
            uom_id = doc.get("uom") or doc.get("unit_of_measure")
            if uom_id:
                item_to_uom[iid] = str(uom_id)
                uom_ids.append(str(uom_id))
        uom_display = await resolve_many_link_displays("unit_of_measure", uom_ids, db)

        # Build line items for template
        line_items = []
        subtotal = 0.0
        for line in lines:
            qty = line.get("quantity_ordered") or 0
            price = line.get("price") or 0.0
            total = qty * price
            subtotal += total

            item_id = line.get("item_id")
            item_label = ""
            if item_id:
                item_label = item_display.get(str(item_id), str(item_id))

            unit_label = "pc"
            if item_id and str(item_id) in item_to_uom:
                unit_label = uom_display.get(item_to_uom[str(item_id)], item_to_uom[str(item_id)])
            line_items.append({
                "description": line.get("item_description") or item_label or "",
                "qty": qty,
                "unit": unit_label,
                "unit_price": f"{price:,.2f}" if price else "-",
                "total": f"{total:,.2f}" if total else "-",
            })

        total_amount = record.get("total_amount") or subtotal

        return {
            "po_number": po_id,
            "po_date": _format_date(record.get("date_ordered")),
            "doc_ref": f"Document Ref: EAM/{po_id}",
            "building": site_name,
            # Company info (static for Panasiatic)
            "company_address": site_data.get("address", ""),
            "company_contact": site_data.get("contact_number", ""),
            # Vendor
            "vendor_name": vendor_name or record.get("vendor_name", ""),
            "vendor_address": vendor_data.get("address", ""),
            "vendor_contact": vendor_data.get("contact_number", "") or vendor_data.get("phone", ""),
            # Ship to (defaults to site)
            "ship_to_name": site_name,
            "ship_to_company": "PANASIATIC CALL CENTERS INC.",
            "ship_to_address": site_data.get("address", ""),
            "ship_to_contact": site_data.get("contact_number", ""),
            # Table header
            "requisitioner": dept_name,
            "delivery_date": "",
            "fob_point": "",
            "terms": "",
            # Line items
            "line_items": line_items,
            # Instructions
            "delivery_instructions": "",
            "special_instructions": [
                "Deliver materials with corresponding delivery receipt / sales invoice.",
                "All items must conform to specifications indicated above.",
                "Warranty as applicable.",
            ],
            # Totals
            "subtotal": f"{subtotal:,.2f}",
            "shipment_handling": "",
            "total_amount": f"{total_amount:,.2f}" if total_amount else "-",
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
