"""
Entity Print Routes
====================
Generate printable HTML preview and PDF download for entity records.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.meta.registry import MetaRegistry
from app.api.dependencies import get_document_service
from app.application.services.documents.document_service import DocumentAppService
from app.application.services.documents.print import render_entity_html, render_with_assembler, html_to_pdf
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service

router = APIRouter(tags=["print"])


@router.get("/{entity}/{record_id}/print", name="print_preview")
async def print_preview(
    entity: str,
    record_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    document_service: DocumentAppService = Depends(get_document_service),
):
    """Return printable HTML for an entity record."""
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    doc = await document_service.get_doc(entity, record_id, as_dict=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")

    html = await _render_html(entity, meta, doc, db)
    return HTMLResponse(content=html)


@router.get("/{entity}/{record_id}/print/pdf", name="print_pdf")
async def print_pdf(
    entity: str,
    record_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    document_service: DocumentAppService = Depends(get_document_service),
):
    """Generate and return a PDF for an entity record."""
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    doc = await document_service.get_doc(entity, record_id, as_dict=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")

    html = await _render_html(entity, meta, doc, db)

    try:
        pdf_bytes = await html_to_pdf(html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"{entity}_{record_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _get_branding(db: AsyncSession) -> dict:
    """Fetch branding settings from the JSON file store, embedding logo as base64."""
    try:
        from app.application.services.branding_service import BrandingService
        from app.infrastructure.settings import BrandingStore
        from app.core.config import settings
        from pathlib import Path
        import base64, mimetypes
        uploads_root = Path(settings.UPLOAD_DIR)
        settings_dir = uploads_root / "settings"
        service = BrandingService(
            store=BrandingStore(settings_dir / "branding.json"),
            assets_dir=settings_dir / "branding",
            uploads_root=uploads_root,
        )
        data = service.get_branding()
        # Convert logo_url (relative /uploads/... path) to base64 data URI
        # so Playwright can render it without needing a running HTTP server
        if data.get("logo_url"):
            logo_rel = data["logo_url"].lstrip("/")  # e.g. "uploads/settings/branding/logo-xxx.png"
            logo_path = Path(logo_rel)
            if not logo_path.is_absolute():
                # Resolve relative to CWD (where FastAPI runs — backend/)
                logo_path = Path.cwd() / logo_rel
            if logo_path.exists():
                mime = mimetypes.guess_type(str(logo_path))[0] or "image/png"
                b64 = base64.b64encode(logo_path.read_bytes()).decode()
                data["logo_url"] = f"data:{mime};base64,{b64}"
        return data
    except Exception:
        pass
    return {"organization_name": "Organization", "description": "", "logo_url": None}


async def _render_html(entity: str, meta, doc: dict, db: AsyncSession) -> str:
    """Try assembler-based rendering first, fall back to generic field rendering."""
    branding = await _get_branding(db)
    assembler_html = await render_with_assembler(entity, doc, db, branding=branding)
    if assembler_html:
        return assembler_html

    fields = [
        f.to_dict() if hasattr(f, "to_dict") else {
            "name": f.name, "label": f.label,
            "field_type": f.field_type,
            "link_entity": getattr(f, "link_entity", None),
        }
        for f in meta.fields
    ]

    # Fetch child table data for inline children
    children_data = []
    record_id = doc.get("id", "") if isinstance(doc, dict) else ""
    if meta.children and record_id:
        from app.application.services.documents.document_query import get_list
        for child_config in meta.children:
            child_entity = child_config.entity
            child_fk = child_config.fk_field
            child_label = child_config.label or child_entity.replace("_", " ").title()

            child_meta = MetaRegistry.get(child_entity)
            if not child_meta:
                continue

            # Build visible columns (non-hidden, non-system fields)
            columns = [
                {"name": f.name, "label": f.label}
                for f in child_meta.fields
                if not f.hidden and f.name not in ("id", "created_at", "updated_at", child_fk)
            ]

            try:
                rows = await get_list(
                    child_entity,
                    filters={child_fk: record_id},
                    db=db,
                    limit=500,
                )
                # Resolve link titles in child rows
                child_link_fields = {f.name: f.link_entity for f in child_meta.fields if f.link_entity}
                for row in rows:
                    row_dict = row if isinstance(row, dict) else {}
                    for fname, lentity in child_link_fields.items():
                        val = row_dict.get(fname)
                        if val and isinstance(doc, dict):
                            lt = doc.get("_link_titles", {})
                            key = f"{lentity}::{val}"
                            if key in lt:
                                row_dict[fname] = lt[key]
            except Exception:
                rows = []

            children_data.append({
                "label": child_label,
                "columns": columns,
                "rows": [r if isinstance(r, dict) else {} for r in rows],
            })

    return render_entity_html(
        entity_name=entity,
        entity_label=meta.label or entity,
        record=doc if isinstance(doc, dict) else {},
        fields=fields,
        link_titles=doc.get("_link_titles") if isinstance(doc, dict) else None,
        children=children_data,
        branding=branding,
    )
