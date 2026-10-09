"""An in-memory audit log; the subscription adapter supplies an order ID."""


class Audit:
    def __init__(self) -> None:
        self._order_ids: list[int] = []

    def record(self, order_id: int) -> None:
        self._order_ids.append(order_id)
        print(f"  Audit.record({order_id}) -> recorded")

    def recorded_orders(self) -> tuple[int, ...]:
        return tuple(self._order_ids)
