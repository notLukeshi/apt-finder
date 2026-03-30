from src.models import Apartment


class PriceFilter:
    def __init__(self, min_price: float, max_price: float):
        self.min_price = min_price
        self.max_price = max_price

    def filter(self, apartments: list[Apartment]) -> list[Apartment]:
        """Filter apartments by price range."""
        return [
            apt for apt in apartments
            if self.min_price <= apt.price <= self.max_price
        ]

    def is_in_range(self, price: float) -> bool:
        """Check if price is in range."""
        return self.min_price <= price <= self.max_price
