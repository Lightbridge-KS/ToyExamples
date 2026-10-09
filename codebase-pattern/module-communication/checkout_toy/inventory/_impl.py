"""Private stock representation and reservation rules."""


class InsufficientStock(ValueError):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]) -> None:
        self._stock = dict(stock)  # Own the state; do not retain the caller's dict.

    def reserve(self, sku: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.available(sku) < quantity:
            raise InsufficientStock(f"not enough {sku}")
        self._stock[sku] -= quantity
        print(f"  Inventory.reserve({sku!r}, {quantity}) -> reserved")

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)
