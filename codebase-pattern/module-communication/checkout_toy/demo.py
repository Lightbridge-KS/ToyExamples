"""Wire the modules, trace success and rejection, then verify the outcomes."""

from .checkout import Checkout
from .inventory import InsufficientStock, Inventory
from .notifications import Notifications
from .orders import OrderReceipt, Orders


def main() -> None:
    # Composition root: choose instances once, then pass them to the workflow.
    inventory = Inventory({"BOOK": 2})
    orders = Orders()
    notifications = Notifications()
    checkout = Checkout(inventory, orders, notifications)

    print("SUCCESS: place one order")
    receipt = checkout.place_order("BOOK", 1)
    assert receipt == OrderReceipt(1, "BOOK", 1)
    assert inventory.available("BOOK") == 1
    assert orders.receipts() == (receipt,)
    assert notifications.confirmations() == (1,)
    print(f"  Checkout returns {receipt}")

    print("\nREJECTED: request more stock than remains")
    try:
        checkout.place_order("BOOK", 2)
    except InsufficientStock as error:
        print(f"  Inventory raises {type(error).__name__}: {error}")
        print("  Checkout stops before creating an order or sending a message")
    else:
        raise AssertionError("expected insufficient stock")

    # Inspect outcomes through public APIs, without reaching into private state.
    assert inventory.available("BOOK") == 1
    assert orders.receipts() == (receipt,)
    assert notifications.confirmations() == (1,)
    print("\nAll outcome checks passed.")


if __name__ == "__main__":
    main()
