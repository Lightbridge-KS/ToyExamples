"""The orchestrator owns the workflow, using only public module APIs."""

from .inventory import Inventory
from .notifications import Notifications
from .orders import OrderReceipt, Orders


class Checkout:
    def __init__(
        self, inventory: Inventory, orders: Orders, notifications: Notifications
    ) -> None:
        self._inventory = inventory
        self._orders = orders
        self._notifications = notifications

    def place_order(self, sku: str, quantity: int) -> OrderReceipt:
        # Ordinary synchronous calls: each must succeed before the next starts.
        self._inventory.reserve(sku, quantity)
        receipt = self._orders.create(sku, quantity)
        self._notifications.send_confirmation(receipt.order_id)
        return receipt
