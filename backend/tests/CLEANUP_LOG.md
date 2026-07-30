# Cleanup Log

Date: 2026-04-20

## Summary

The previous backend test suite was removed and replaced because it did not match the current clean-architecture structure or the requested test scope.

The deleted suite was dominated by workflow, business-logic, and end-to-end process tests. Those files exercised orchestration flows that the current sprint explicitly excludes.

## Deleted Root-Level Files

These files were removed because they were outdated, duplicated, workflow-heavy, or mixed multiple concerns in a way that did not fit the new layered structure.

- `conftest.py`
- `run_all_flows.py`
- `seed_test_db.py`
- `setup_local_test_db.py`
- `test_api_integration.py`
- `test_architecture.py`
- `test_asset_flows.py`
- `test_asset_property_hook.py`
- `test_asset_workflow_e2e.py`
- `test_atomic_save_e2e.py`
- `test_attachments_and_depends_on.py`
- `test_audit_log_validation.py`
- `test_business_logic_e2e.py`
- `test_business_logic_flows.py`
- `test_computer_pm_flow_e2e.py`
- `test_core_entities.py`
- `test_dashboard_access.py`
- `test_email_notification.py`
- `test_incident_print.py`
- `test_item_issue_return_e2e.py`
- `test_login.py`
- `test_maint_flows.py`
- `test_maintenance_workflow_e2e.py`
- `test_metadata_sync.py`
- `test_permissions.py`
- `test_permissions_e2e.py`
- `test_pm_calendar_2026_04_16.py`
- `test_pm_date_plotting_flow.py`
- `test_po_feature_flag.py`
- `test_pr_flows.py`
- `test_pr_workflow_e2e.py`
- `test_purchasing_stores_e2e.py`
- `test_sc_flows.py`
- `test_services_unit.py`
- `test_sorting_fix.py`
- `test_stock_count_e2e.py`
- `test_stock_count_inventory_adjustment_e2e.py`
- `test_subscription_flow.py`
- `test_wo_filters_and_transfer_e2e.py`
- `test_work_order_manual_e2e.py`
- `test_work_order_print.py`
- `test_workflow_apply.py`
- `test_workflow_colors.py`
- `test_workflow_enhancements.py`
- `validate_todo.py`

Reasons:

- Business logic and workflow orchestration tests were explicitly out of scope.
- Several files duplicated permission, workflow, or CRUD coverage.
- Some files were date-specific, script-like, or manual runners instead of stable pytest cases.
- Many tests targeted pre-refactor service paths and older suite organization.

## Deleted Subdirectories

These directories were removed because they were built around business-process phases instead of clean architecture seams.

- `bu_logic/`
- `setup/`

Removed files from those directories included:

- `bu_logic/helpers.py`
- `bu_logic/run_all.py`
- `bu_logic/test_phase2_1_asset_installation.py`
- `bu_logic/test_phase2_procurement.py`
- `bu_logic/test_phase3_1_emergency.py`
- `bu_logic/test_phase3_maintenance.py`
- `bu_logic/test_phase4_1_issuing_returning.py`
- `bu_logic/test_phase4_work_management.py`
- `bu_logic/test_phase5_stock_count.py`
- `setup/conftest.py`
- `setup/test_full_setup_pipeline.py`
- `setup/test_seed_reference_data.py`
- `setup/test_seed_roles.py`
- `setup/test_seed_workflow.py`
- `setup/test_superadmin_creation.py`

Reasons:

- The `bu_logic` suite was entirely workflow and business-process driven.
- The `setup` suite did not fit the requested target structure of `api`, `integration`, `repositories`, `schemas`, and `infrastructure`.

## Replacement Structure

The backend test suite was rewritten into the requested grouped layout:

- `tests/api/`
- `tests/integration/`
- `tests/repositories/`
- `tests/schemas/`
- `tests/infrastructure/`
- `tests/conftest.py`

## Replacement Files

The new suite now consists of the following date-stamped test files:

- `api/test_auth_api_20260420.py`
- `api/test_route_contracts_20260420.py`
- `integration/test_http_integration_20260420.py`
- `integration/test_repository_roundtrip_20260420.py`
- `repositories/test_entity_repository_20260420.py`
- `repositories/test_document_repository_20260420.py`
- `repositories/test_auth_workflow_repository_20260420.py`
- `schemas/test_base_schemas_20260420.py`
- `schemas/test_user_role_schemas_20260420.py`
- `infrastructure/test_settings_and_wiring_20260420.py`

## Notes

- Integration tests now use the local PostgreSQL database directly.
- DB-backed tests avoid workflow orchestration and focus on idempotent repository and HTTP read paths.
- Shared fixtures were consolidated into a single root `conftest.py`.
