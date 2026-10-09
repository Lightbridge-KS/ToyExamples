"""Public event contract owned by Orders."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderPlaced:
    order_id: int
    sku: str
    quantity: int
