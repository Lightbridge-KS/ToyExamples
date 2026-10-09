"""An in-memory inbox stands in for a real delivery mechanism."""


class Notifications:
    def __init__(self) -> None:
        self._confirmations: list[int] = []

    def send_confirmation(self, order_id: int) -> None:
        self._confirmations.append(order_id)
        print(f"  Notifications.send_confirmation({order_id}) -> delivered")

    def confirmations(self) -> tuple[int, ...]:
        return tuple(self._confirmations)
