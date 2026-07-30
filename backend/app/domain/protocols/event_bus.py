"""
Domain Event Bus Protocol
=========================
Abstract interface for publishing and subscribing to domain events.
"""
from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class DomainEventBusProtocol(Protocol):
    """Interface for domain event publishing and subscription."""

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish a domain event."""
        ...

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to a domain event type."""
        ...
