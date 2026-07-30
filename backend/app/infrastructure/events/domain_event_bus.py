"""
Domain Event Bus
================
In-process implementation of DomainEventBusProtocol.
Supports sync handlers; async handlers are scheduled via asyncio.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DomainEventBus:
    """Simple in-process event bus for domain events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publish an event to all subscribed handlers.
        Async handlers are scheduled on the running event loop.
        """
        for handler in self._handlers.get(event_type, []):
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(result)
                    else:
                        loop.run_until_complete(result)
            except Exception:
                logger.exception(
                    "Error in event handler for %s", event_type
                )

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._handlers.clear()


# Singleton instance
domain_event_bus = DomainEventBus()
