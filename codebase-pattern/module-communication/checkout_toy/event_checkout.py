"""Keep required work explicit; announce its outcome to optional subscribers."""

from .event_bus import EventBus
from .inventory import Inventory
from .orders import OrderPlaced, OrderReceipt, Orders


class EventCheckout:
    def __init__(
        self, inventory: Inventory, orders: Orders, bus: EventBus[OrderPlaced]
    ) -> None:
        self._inventory = inventory
        self._orders = orders
        self._bus = bus

    def place_order(self, sku: str, quantity: int) -> OrderReceipt:
        self._inventory.reserve(sku, quantity)
        receipt = self._orders.create(sku, quantity)
        self._bus.publish(OrderPlaced(receipt.order_id, receipt.sku, receipt.quantity))
        return receipt
