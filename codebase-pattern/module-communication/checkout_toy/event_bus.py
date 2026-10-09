"""A synchronous pub/sub channel: every subscriber receives each publication."""

from collections.abc import Callable
from typing import Generic, TypeVar

Event = TypeVar("Event")


class EventBus(Generic[Event]):
    def __init__(self) -> None:
        self._handlers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._handlers.append(handler)

    def publish(self, event: Event) -> None:
        print(f"  EventBus.publish({event!r}) -> {len(self._handlers)} subscriber(s)")
        # Inline, in registration order. An exception stops this loop.
        for handler in tuple(self._handlers):
            handler(event)
