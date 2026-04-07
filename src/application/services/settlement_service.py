"""Settlement service - handles settlement management operations."""

from datetime import date
from decimal import Decimal

from src.domain.errors import SettlementNotFoundError
from src.application.dto.payment_dto import CreateSettlementRequestDTO
from src.application.services.payment_service import PaymentService
from src.infrastructure.repositories.base_repository import PaymentRepository


class SettlementService:
    """Service for settlement CRUD operations."""

    def __init__(
        self,
        repository: PaymentRepository,
        payment_service: PaymentService,
    ):
        """Initialize with repository and payment service."""
        self.repository = repository
        self.payment_service = payment_service

    def add_settlement(
        self,
        creditor: str,
        total_amount: float,
        monthly_payment: float,
        first_due_date: date,
        payment_day_of_month: int | None = None,
    ) -> None:
        """Add a new settlement with auto-generated payment schedule."""
        request = CreateSettlementRequestDTO(
            creditor=creditor,
            total_amount=Decimal(str(total_amount)),
            monthly_payment=Decimal(str(monthly_payment)),
            first_due_date=first_due_date,
            payment_day_of_month=payment_day_of_month,
        )

        self.payment_service.create_settlement(request)

    def delete_settlement(self, creditor: str) -> None:
        """Delete a settlement and all its payments."""
        settlement = self.repository.get_settlement(creditor)
        if not settlement:
            raise SettlementNotFoundError(f"Settlement not found: {creditor}")

        self.repository.remove_settlement(creditor)

    def get_creditor_names(self) -> list[str]:
        """Get list of all creditor names."""
        settlements = self.repository.get_all_settlements()
        return [s.creditor for s in settlements]
