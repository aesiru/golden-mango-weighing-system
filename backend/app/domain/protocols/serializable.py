"""
Serializable Protocol
=====================
Types that implement this protocol define their own serialization.
"""
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Serializable(Protocol):
    """Any object that can serialize itself to a dict."""

    def to_serializable(self) -> Any: ...
