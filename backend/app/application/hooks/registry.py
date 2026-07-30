"""
Hook Registry
==============
Decorator-based hook registration system.
Replaces the if/elif chain in services/hooks.py with an OCP-compliant registry.

Usage in modules:
    from app.application.hooks.registry import hook_registry

    @hook_registry.before_save("asset")
    async def asset_before_save(doc, ctx):
        ...

    @hook_registry.after_save("asset")
    async def asset_after_save(doc, ctx):
        ...

    @hook_registry.workflow("asset")
    async def asset_workflow(doc, ctx):
        ...
"""
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class HookEntry:
    """A registered hook function."""
    entity: str
    func: Callable
    priority: int = 0


class HookRegistry:
    """Registry for entity lifecycle hooks."""

    def __init__(self):
        self._before_save: dict[str, list[HookEntry]] = {}
        self._after_save: dict[str, list[HookEntry]] = {}
        self._after_delete: dict[str, list[HookEntry]] = {}
        self._workflow: dict[str, list[HookEntry]] = {}

    # ------------------------------------------------------------------
    # Decorators
    # ------------------------------------------------------------------

    def before_save(self, entity: str, priority: int = 0):
        """Register a before_save hook for an entity."""
        def decorator(func: Callable) -> Callable:
            entry = HookEntry(entity=entity, func=func, priority=priority)
            self._before_save.setdefault(entity, []).append(entry)
            self._before_save[entity].sort(key=lambda e: e.priority)
            return func
        return decorator

    def after_save(self, entity: str, priority: int = 0):
        """Register an after_save hook for an entity."""
        def decorator(func: Callable) -> Callable:
            entry = HookEntry(entity=entity, func=func, priority=priority)
            self._after_save.setdefault(entity, []).append(entry)
            self._after_save[entity].sort(key=lambda e: e.priority)
            return func
        return decorator

    def after_delete(self, entity: str, priority: int = 0):
        """Register an after_delete hook for an entity."""
        def decorator(func: Callable) -> Callable:
            entry = HookEntry(entity=entity, func=func, priority=priority)
            self._after_delete.setdefault(entity, []).append(entry)
            self._after_delete[entity].sort(key=lambda e: e.priority)
            return func
        return decorator

    def workflow(self, entity: str, priority: int = 0):
        """Register a workflow hook for an entity."""
        def decorator(func: Callable) -> Callable:
            entry = HookEntry(entity=entity, func=func, priority=priority)
            self._workflow.setdefault(entity, []).append(entry)
            self._workflow[entity].sort(key=lambda e: e.priority)
            return func
        return decorator

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run_before_save(self, entity: str, doc: dict, ctx: Any) -> tuple[dict, Optional[dict]]:
        """Run all before_save hooks for an entity. Returns (modified_doc, errors)."""
        hooks = self._before_save.get(entity, [])
        for hook in hooks:
            result = await hook.func(doc, ctx)
            if isinstance(result, tuple):
                doc, errors = result
                if errors:
                    return doc, errors
            elif isinstance(result, dict):
                doc = result
        return doc, None

    async def run_after_save(self, entity: str, doc: Any, ctx: Any) -> Optional[dict]:
        """Run all after_save hooks for an entity. Returns last hook result."""
        hooks = self._after_save.get(entity, [])
        last_result = None
        for hook in hooks:
            result = await hook.func(doc, ctx)
            if result is not None:
                last_result = result
        return last_result

    async def run_after_delete(self, entity: str, doc: Any, ctx: Any) -> Optional[dict]:
        """Run all after_delete hooks for an entity. Returns last hook result."""
        hooks = self._after_delete.get(entity, [])
        last_result = None
        for hook in hooks:
            result = await hook.func(doc, ctx)
            if result is not None:
                last_result = result
        return last_result

    async def run_workflow(self, entity: str, ctx: Any) -> dict:
        """Run workflow hooks for an entity. Returns result dict."""
        hooks = self._workflow.get(entity, [])
        for hook in hooks:
            result = await hook.func(ctx)
            if result and result.get("status") == "error":
                return result
            if result:
                return result
        return {"status": "success", "message": f"No workflow hook for '{entity}'"}

    # ------------------------------------------------------------------
    # Aliases (used by entity_crud.py and entity_workflow.py)
    # ------------------------------------------------------------------

    async def execute_before_save(self, entity: str, doc: dict, ctx: Any):
        """Alias for run_before_save with compatible return format."""
        modified_doc, errors = await self.run_before_save(entity, doc, ctx)
        if errors:
            return {"errors": errors}
        return {"data": modified_doc}

    async def execute_after_save(self, entity: str, doc: Any, ctx: Any):
        """Alias for run_after_save."""
        return await self.run_after_save(entity, doc, ctx)

    async def execute_after_delete(self, entity: str, doc: Any, ctx: Any):
        """Alias for run_after_delete."""
        return await self.run_after_delete(entity, doc, ctx)

    async def execute_workflow(self, entity: str, ctx: Any) -> dict:
        """Alias for run_workflow."""
        return await self.run_workflow(entity, ctx)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def has_hooks(self, entity: str) -> bool:
        return bool(
            self._before_save.get(entity)
            or self._after_save.get(entity)
            or self._after_delete.get(entity)
            or self._workflow.get(entity)
        )

    def list_entities(self) -> set[str]:
        entities = set()
        entities.update(self._before_save.keys())
        entities.update(self._after_save.keys())
        entities.update(self._after_delete.keys())
        entities.update(self._workflow.keys())
        return entities


# Global singleton
hook_registry = HookRegistry()
