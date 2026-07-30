"""
Document Service
================
Backward-compatible facade that re-exports from the CLEAN architecture services:
- DocumentAppService (read-only operations)
- document_mutation.py (write operations - updated to use new services internally)

Usage remains unchanged:
    from app.application.services.documents.document import get_doc, new_doc, save_doc, get_meta, get_value

Last Updated: 2026-04-19
"""
# Re-export query operations from legacy document_query for backward compatibility
# These functions are used by many modules and will be migrated gradually
from app.application.services.documents.document_query import (  # noqa: F401
    get_meta,
    get_doc,
    get_value,
    get_list,
    _get_model,
    _record_to_dict,
)

# Re-export mutation operations (updated to use new services internally)
from app.application.services.documents.document_mutation import (  # noqa: F401
    new_doc,
    save_doc,
    insert_doc,
    delete_doc,
    apply_workflow_state,
)
