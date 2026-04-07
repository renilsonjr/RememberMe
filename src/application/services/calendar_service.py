"""Calendar service - handles Google Calendar synchronization."""

from src.domain.payment import Payment
from src.infrastructure.calendar.calendar_gateway import CalendarGateway
from src.infrastructure.repositories.base_repository import PaymentRepository


class CalendarService:
    """Service for synchronizing payments with Google Calendar."""

    def __init__(
        self,
        repository: PaymentRepository,
        calendar_gateway: CalendarGateway,
    ):
        """Initialize with repository and calendar gateway."""
        self.repository = repository
        self.calendar_gateway = calendar_gateway

    def sync_upcoming_payments(self, days: int = 14) -> list[str]:
        """
        Sync upcoming payments to Google Calendar.

        Returns a list of created event IDs.
        """
        payments = self.repository.get_all_payments()
        upcoming = [p for p in payments if p.is_due_soon(days)]

        if not upcoming:
            return []

        return self.calendar_gateway.create_events(upcoming)

    def sync_all_payments(self) -> list[str]:
        """Sync all future payments to Google Calendar."""
        payments = self.repository.get_all_payments()
        return self.calendar_gateway.create_events(payments)
