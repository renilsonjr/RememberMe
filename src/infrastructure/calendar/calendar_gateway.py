"""Abstract calendar gateway interface."""

from typing import Protocol

from src.domain.payment import Payment


class CalendarGateway(Protocol):
    """Abstract interface for calendar operations."""

    def create_event(self, payment: Payment, payments_remaining: int) -> str:
        """
        Create a calendar event for a payment.

        Args:
            payment: The payment to create an event for
            payments_remaining: Number of remaining payments for this creditor

        Returns:
            Event ID from the calendar service
        """
        ...

    def create_events(self, payments: list[Payment]) -> list[str]:
        """Create multiple calendar events."""
        ...
