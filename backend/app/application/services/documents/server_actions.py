"""
Server actions registry and executor.

Server actions are custom backend functions that can be invoked via the API.
They are registered per entity and can be called from the frontend.

Supports two calling conventions:
1. Legacy (decorator): func(ctx: ActionContext) -> dict
2. Frappe-style (JSON method path): func(doc, db, user) -> dict
   - Auto-wrapped when loaded via load_from_handler_path()
"""
from typing import Any, Callable, Optional
from dataclasses import dataclass
import asyncio
import importlib
import inspect


@dataclass
class ActionContext:
    """Context passed to server action functions."""
    db: Any
    user: Any
    entity_name: str
    record_id: Optional[str]
    params: dict[str, Any]


ActionFunction = Callable[[ActionContext], Any]


class ServerActionsRegistry:
    """Registry for server actions."""
    
    def __init__(self):
        self._actions: dict[str, dict[str, ActionFunction]] = {}
    
    def register(self, entity: str, action_name: str):
        """Decorator to register a server action."""
        def decorator(func: ActionFunction) -> ActionFunction:
            self.register_action(entity, action_name, func)
            return func
        return decorator
    
    def register_action(self, entity: str, action_name: str, func: ActionFunction):
        """Register a server action for an entity."""
        if entity not in self._actions:
            self._actions[entity] = {}
        self._actions[entity][action_name] = func
    
    def get_action(self, entity: str, action_name: str) -> Optional[ActionFunction]:
        """Get a server action function."""
        return self._actions.get(entity, {}).get(action_name)
    
    def get_actions(self, entity: str) -> list[str]:
        """Get all action names for an entity."""
        return list(self._actions.get(entity, {}).keys())
    
    async def execute(
        self, 
        entity: str, 
        action_name: str, 
        ctx: ActionContext
    ) -> dict[str, Any]:
        """Execute a server action.
        
        Returns the result dict directly from the handler.
        Handlers are expected to return {"status": "success/error", "message": ..., ...}
        """
        func = self.get_action(entity, action_name)
        if not func:
            return {
                "status": "error",
                "message": f"Server action '{action_name}' not found for entity '{entity}'"
            }
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(ctx)
            else:
                result = func(ctx)
            
            # If handler returns a dict with status, return it directly (no double-wrap)
            if isinstance(result, dict) and "status" in result:
                return result
            
            # Fallback: wrap raw return values
            return {
                "status": "success",
                "message": f"Action '{action_name}' executed successfully",
                "data": result
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def load_from_handler_path(self, entity: str, action_name: str, handler_path: str):
        """Load a Frappe-style handler from a dotted module path and register it.
        
        Frappe-style handlers have signature: async def handler(doc, db, user) -> dict
        This method wraps them to accept ActionContext.
        """
        try:
            module_path, func_name = handler_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            
            # Check if it's already ActionContext-style (has single 'ctx' param)
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            if len(param_names) == 1 and param_names[0] in ('ctx', 'context'):
                # Already ActionContext-style, register directly
                self.register_action(entity, action_name, func)
            else:
                # Frappe-style: wrap (doc, db, user[, payload]) -> ActionContext adapter
                # If the handler has a 4th 'payload' param, pass ctx.params["payload"] too
                accepts_payload = len(param_names) >= 4 or "payload" in param_names
                async def wrapper(ctx: ActionContext, _fn=func, _ap=accepts_payload):
                    doc = ctx.params.get("doc")
                    payload = ctx.params.get("payload")
                    if _ap:
                        return await _fn(doc, ctx.db, ctx.user, payload) if asyncio.iscoroutinefunction(_fn) else _fn(doc, ctx.db, ctx.user, payload)
                    return await _fn(doc, ctx.db, ctx.user) if asyncio.iscoroutinefunction(_fn) else _fn(doc, ctx.db, ctx.user)
                
                self.register_action(entity, action_name, wrapper)
        except Exception as e:
            print(f"Failed to load server action {handler_path}: {e}")


server_actions = ServerActionsRegistry()
