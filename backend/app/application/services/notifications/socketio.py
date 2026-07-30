"""
Socket.IO manager for realtime updates.

Emits events when entities are created, updated, deleted, or workflow transitions occur.
"""
import socketio
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.socketio_cors_origins,
    ping_interval=25,
    ping_timeout=60,
    max_http_buffer_size=1e8,
)


class SocketIOManager:
    """Manager for Socket.IO events."""
    
    def __init__(self, server: socketio.AsyncServer):
        self.sio = server
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup Socket.IO event handlers."""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            origin = environ.get("HTTP_ORIGIN")
            remote = environ.get("REMOTE_ADDR")
            print(f"Client connected: {sid} origin={origin} remote={remote} auth={auth}")
        
        @self.sio.event
        async def disconnect(sid):
            print(f"Client disconnected: {sid}")
        
        @self.sio.event
        async def join_entity(sid, data):
            """Join a room for entity updates."""
            entity = data.get("entity")
            if entity:
                await self.sio.enter_room(sid, f"entity:{entity}")
                print(f"Client {sid} joined room entity:{entity}")
        
        @self.sio.event
        async def leave_entity(sid, data):
            """Leave a room for entity updates."""
            entity = data.get("entity")
            if entity:
                await self.sio.leave_room(sid, f"entity:{entity}")
                print(f"Client {sid} left room entity:{entity}")
    
    async def emit_entity_event(
        self,
        entity: str,
        event_type: str,
        data: dict[str, Any],
        record_id: Optional[str] = None
    ):
        """
        Emit an entity event to all clients in the entity room.
        
        event_type: created, updated, deleted, workflow
        """
        event_data = {
            "entity": entity,
            "type": event_type,
            "record_id": record_id,
            "data": data,
        }
        print(f"Emitting entity:{event_type} and entity:change entity={entity} record_id={record_id}")
        await self.sio.emit(
            f"entity:{event_type}",
            event_data,
            room=f"entity:{entity}"
        )
        await self.sio.emit("entity:change", event_data)
    
    async def emit_created(self, entity: str, record: dict[str, Any]):
        """Emit entity created event."""
        await self.emit_entity_event(entity, "created", record, record.get("id"))
    
    async def emit_updated(self, entity: str, record: dict[str, Any]):
        """Emit entity updated event."""
        await self.emit_entity_event(entity, "updated", record, record.get("id"))
    
    async def emit_deleted(self, entity: str, record_id: str):
        """Emit entity deleted event."""
        await self.emit_entity_event(entity, "deleted", {"id": record_id}, record_id)
    
    async def emit_workflow(self, entity: str, record: dict[str, Any], action: str, from_state: str, to_state: str):
        """Emit workflow transition event."""
        await self.emit_entity_event(
            entity,
            "workflow",
            {
                **record,
                "workflow_action": action,
                "from_state": from_state,
                "to_state": to_state,
            },
            record.get("id")
        )

    async def emit_post_save(self, entity: str, record: dict[str, Any], action: str, hook_result: Optional[dict] = None):
        """Emit post-save hook execution event."""
        message = None
        if hook_result and isinstance(hook_result, dict):
            message = hook_result.get("message") or None

        event_data = {
            "entity": entity,
            "action": action,  # "create" or "update"
            "record_id": record.get("id"),
            "record": record,
            "hook_result": hook_result,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),  # Convert to ISO string
        }
        print(f"Emitting post_save event for entity={entity} action={action} record_id={record.get('id')}")
        await self.sio.emit("post_save", event_data)
        await self.sio.emit("entity:post_save", event_data, room=f"entity:{entity}")

    async def emit_meta_change(self, scope: str, data: dict[str, Any]):
        event_data = {
            "scope": scope,
            "data": data,
        }
        print(f"Emitting meta:change scope={scope}")
        await self.sio.emit("meta:change", event_data)


socket_manager = SocketIOManager(sio)
