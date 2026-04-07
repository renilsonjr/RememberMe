"""Abstract repository interface."""

from typing import Protocol

from src.domain.payment import Payment, Settlement


class PaymentRepository(Protocol):
    """Abstract repository interface for payment data access."""

    def get_all_payments(self) -> list[Payment]:
        """Get all payments from storage."""
        ...

    def get_all_settlements(self) -> list[Settlement]:
        """Get all settlements (grouped payments by creditor)."""
        ...

    def get_settlement(self, creditor: str) -> Settlement | None:
        """Get a single settlement by creditor name."""
        ...

    def add_settlement(self, settlement: Settlement) -> None:
        """Add a new settlement to storage."""
        ...

    def remove_settlement(self, creditor: str) -> None:
        """Remove a settlement from storage."""
        ...

    def update_settlement(self, settlement: Settlement) -> None:
        """Update an existing settlement."""
        ...
