from typing import Any, Dict, List
import asyncio
import base64
from datetime import date, datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document_service import DocumentAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.application.services.documents.print_resolver import (
    resolve_link_display,
    resolve_many_link_displays,
)
from app.application.services.documents.print_formatters import format_date, format_datetime
from app.core.config import settings


class IncidentAssembler:
    """Assembles print context for incident entity."""

    entity_name = "incident"

    def get_template_name(self) -> str:
        return "incident.html"

    async def assemble(self, record: dict, db: AsyncSession) -> dict[str, Any]:
        incident_id = record.get("id", "")

        # Create document service
        document_repo = DocumentRepository(db)
        document_service = DocumentAppService(document_repo)

        # Resolve link displays for header
        site_name = await resolve_link_display("site", record.get("site"), db)
        department_name = await resolve_link_display("department", record.get("department"), db)
        location_name = await resolve_link_display("location", record.get("location"), db)
        asset_name = await resolve_link_display("asset", record.get("asset"), db)
        reported_by_name = await resolve_link_display("user", record.get("reported_by"), db)
        assigned_to_name = await resolve_link_display("user", record.get("assigned_to"), db)

        # Fetch attachments for this incident
        attachments = await document_service.get_list(
            "core_attachment",
            filters={"entity_name": "incident", "record_id": incident_id},
            order_by="created_at",
        )

        # Filter for image attachments only
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        photo_attachments = []
        
        for attachment in attachments:
            file_name = attachment.get("file_name", "").lower()
            original_name = attachment.get("original_name", "").lower()
            
            # Check if file is an image based on extension
            is_image = (
                any(file_name.endswith(ext) for ext in image_extensions) or
                any(original_name.endswith(ext) for ext in image_extensions)
            )
            
            if is_image:
                # Read file content and convert to base64 for embedding
                file_path = attachment.get("file_path")
                base64_data = None
                mime_type = attachment.get("mime_type", "image/jpeg")
                
                if file_path:
                    try:
                        # file_path already includes "uploads/" prefix, resolve relative to backend directory
                        full_path = Path.cwd() / file_path.lstrip("/")
                        if full_path.exists():
                            with open(full_path, "rb") as f:
                                base64_data = base64.b64encode(f.read()).decode()
                    except Exception:
                        pass  # If file can't be read, skip base64 embedding
                
                photo_attachments.append({
                    "id": attachment.get("id"),
                    "file_name": attachment.get("file_name"),
                    "original_name": attachment.get("original_name") or attachment.get("file_name"),
                    "file_path": attachment.get("file_path"),
                    "mime_type": mime_type,
                    "description": attachment.get("description", ""),
                    "created_at": format_datetime(attachment.get("created_at")),
                    "base64_data": base64_data,  # Embed base64 for print
                })

        return {
            "incident": {
                "id": incident_id,
                "title": record.get("title", ""),
                "description": record.get("description", ""),
                "incident_type": record.get("incident_type", ""),
                "severity": record.get("severity", ""),
                "status": record.get("workflow_state", ""),
                "date_occurred": format_date(record.get("date_occurred")),
                "time_occurred": record.get("time_occurred", ""),
                "reported_date": format_date(record.get("reported_date")),
                "site": site_name,
                "department": department_name,
                "location": location_name,
                "asset": asset_name,
                "reported_by": reported_by_name,
                "assigned_to": assigned_to_name,
                "witnesses": record.get("witnesses", ""),
                "immediate_action": record.get("immediate_action", ""),
                "root_cause": record.get("root_cause", ""),
                "corrective_action": record.get("corrective_action", ""),
                "preventive_action": record.get("preventive_action", ""),
            },
            "photos": photo_attachments,
            "branding": {"organization_name": "Organization"},
            "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "record_id": incident_id,
            "record": record,
        }
