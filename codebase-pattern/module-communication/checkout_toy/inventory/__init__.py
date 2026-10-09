"""Inventory's public API; callers never import _impl directly."""

from ._impl import InsufficientStock, Inventory

__all__ = ["InsufficientStock", "Inventory"]
