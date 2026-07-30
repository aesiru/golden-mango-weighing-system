from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.meta.registry import EntityMeta
from app.application.services.integrations import import_export as ie


ImportMode = str


@dataclass
class ImportValidationSummary:
    valid: bool
    errors: list[dict[str, Any]]
    rows: int
    warnings: list[str]


@dataclass
class ImportExecutionSummary:
    count: int
    duplicates: int = 0
    updated: int = 0
    missing: int = 0


class ImportExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_import(
        self,
        meta: EntityMeta,
        headers: list[str],
        rows: list[dict[str, Any]],
        mode: ImportMode = "create",
    ) -> ImportValidationSummary:
        header_errors = ie.validate_headers(meta, headers)
        if header_errors:
            return ImportValidationSummary(
                valid=False,
                errors=[{"row": 1, "errors": [{"field": "header", "message": error} for error in header_errors]}],
                rows=len(rows),
                warnings=[],
            )

        _, errors = await ie.validate_rows(self.db, meta, rows, mode=mode)
        warnings: list[str] = []
        if mode == "update":
            warnings.append("Update mode requires valid existing record IDs in the import data.")

        return ImportValidationSummary(
            valid=not errors,
            errors=errors,
            rows=len(rows),
            warnings=warnings,
        )

    async def execute_import(
        self,
        meta: EntityMeta,
        headers: list[str],
        rows: list[dict[str, Any]],
        mode: ImportMode = "create",
    ) -> ImportExecutionSummary:
        validation = await self.validate_import(meta, headers, rows, mode=mode)
        if not validation.valid:
            raise ValueError("Validation failed")

        validated, _ = await ie.validate_rows(self.db, meta, rows, mode=mode)

        if mode == "update":
            updated_count, missing = await ie.update_records(self.db, meta, validated)
            return ImportExecutionSummary(count=updated_count, updated=updated_count, missing=len(missing))

        created_count, duplicates = await ie.create_records(self.db, meta, validated)
        return ImportExecutionSummary(count=created_count, duplicates=len(duplicates))
