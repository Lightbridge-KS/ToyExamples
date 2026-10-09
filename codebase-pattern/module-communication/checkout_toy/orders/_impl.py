"""Private order storage; no knowledge of inventory or notifications."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderReceipt:
    order_id: int
    sku: str
    quantity: int


class Orders:
    def __init__(self) -> None:
        self._receipts: list[OrderReceipt] = []

    def create(self, sku: str, quantity: int) -> OrderReceipt:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        receipt = OrderReceipt(len(self._receipts) + 1, sku, quantity)
        self._receipts.append(receipt)
        print(f"  Orders.create({sku!r}, {quantity}) -> order #{receipt.order_id}")
        return receipt

    def receipts(self) -> tuple[OrderReceipt, ...]:
        return tuple(self._receipts)  # A snapshot, not the mutable internal list.
