"""Compare fan-out, a new subscriber, early rejection, and a failing subscriber."""

from .audit import Audit
from .event_bus import EventBus
from .event_checkout import EventCheckout
from .inventory import InsufficientStock, Inventory
from .notifications import Notifications
from .orders import OrderPlaced, Orders


def demo_subscribers() -> None:
    inventory, orders, notifications = Inventory({"BOOK": 3}), Orders(), Notifications()
    bus = EventBus[OrderPlaced]()
    # Subscription adapters translate the event into each module's public call.
    bus.subscribe(lambda event: notifications.send_confirmation(event.order_id))
    checkout = EventCheckout(inventory, orders, bus)

    print("ONE SUBSCRIBER: notifications")
    first = checkout.place_order("BOOK", 1)
    assert notifications.confirmations() == (first.order_id,)

    print("\nADD AUDIT: same publisher, one more subscription")
    audit = Audit()
    bus.subscribe(lambda event: audit.record(event.order_id))
    assert audit.recorded_orders() == ()  # Subscribing does not replay the first event.
    second = checkout.place_order("BOOK", 1)
    assert orders.receipts() == (first, second)
    assert notifications.confirmations() == (1, 2)
    assert audit.recorded_orders() == (2,)
    assert inventory.available("BOOK") == 1

    print("\nREJECTED: no order created, so no event published")
    try:
        checkout.place_order("BOOK", 2)
    except InsufficientStock as error:
        print(f"  Inventory raises {type(error).__name__}: {error}")
    else:
        raise AssertionError("expected insufficient stock")
    assert inventory.available("BOOK") == 1
    assert orders.receipts() == (first, second)
    assert notifications.confirmations() == (1, 2)
    assert audit.recorded_orders() == (2,)


def demo_handler_failure() -> None:
    print("\nHANDLER FAILURE: a fresh checkout with a failing first subscriber")
    inventory, orders, audit = Inventory({"BOOK": 1}), Orders(), Audit()
    bus = EventBus[OrderPlaced]()

    def fail_delivery(event: OrderPlaced) -> None:
        print(f"  Notification subscriber for order #{event.order_id} -> raises")
        raise RuntimeError("delivery failed")

    bus.subscribe(fail_delivery)
    bus.subscribe(lambda event: audit.record(event.order_id))
    try:
        EventCheckout(inventory, orders, bus).place_order("BOOK", 1)
    except RuntimeError as error:
        print(f"  Checkout raises {type(error).__name__}: {error}")
    else:
        raise AssertionError("expected delivery failure")
    assert inventory.available("BOOK") == 0
    assert len(orders.receipts()) == 1
    assert audit.recorded_orders() == ()
    print("  Stock reserved; order exists; later Audit subscriber never ran")


if __name__ == "__main__":
    demo_subscribers()
    demo_handler_failure()
    print("\nAll event-bus outcome checks passed.")
