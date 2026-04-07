"""Payment service - handles payment-related use cases."""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from src.domain.payment import Payment, Settlement
from src.domain.errors import InvalidSettlementError
from src.application.dto.payment_dto import (
    PaymentDTO,
    SettlementSummaryDTO,
    CreateSettlementRequestDTO,
    MonthlySummaryDTO,
)
from src.infrastructure.repositories.base_repository import PaymentRepository


class PaymentService:
    """Service for managing payments and settlements."""

    def __init__(self, repository: PaymentRepository):
        """Initialize with a payment repository."""
        self.repository = repository

    def get_all_payments(self) -> list[PaymentDTO]:
        """Get all payments as DTOs."""
        payments = self.repository.get_all_payments()
        return [self._payment_to_dto(p) for p in payments]

    def get_upcoming_payments(self, days: int = 14) -> list[PaymentDTO]:
        """Get all payments due within N days."""
        all_payments = self.repository.get_all_payments()
        upcoming = [p for p in all_payments if p.is_due_soon(days)]
        return [self._payment_to_dto(p) for p in upcoming]

    def get_all_summaries(self) -> list[SettlementSummaryDTO]:
        """Get summaries of all creditors for dashboard."""
        settlements = self.repository.get_all_settlements()
        return [self._settlement_to_summary(s) for s in settlements]

    def get_settlement_summary(self, creditor: str) -> SettlementSummaryDTO | None:
        """Get summary for a specific creditor."""
        settlement = self.repository.get_settlement(creditor)
        if not settlement:
            return None
        return self._settlement_to_summary(settlement)

    def get_monthly_summary(self) -> list[MonthlySummaryDTO]:
        """Get monthly summary of future payments."""
        payments = self.repository.get_all_payments()
        today = date.today()

        # Group future payments by (year, month)
        buckets: dict[tuple[int, int], Decimal] = {}
        for p in payments:
            if p.due_date < today:
                continue
            key = (p.due_date.year, p.due_date.month)
            buckets[key] = buckets.get(key, Decimal("0")) + p.amount

        # Convert to DTOs sorted chronologically
        result = []
        for (year, month), total in sorted(buckets.items()):
            result.append(
                MonthlySummaryDTO(
                    year=year,
                    month=month,
                    total_due=total,
                    total_paid=0,  # Placeholder - not tracked yet
                )
            )
        return result

    def create_settlement(
        self, request: CreateSettlementRequestDTO
    ) -> Settlement:
        """Create a new settlement with generated payment schedule."""
        payments = self._generate_payment_schedule(
            request.creditor,
            request.total_amount,
            request.monthly_payment,
            request.first_due_date,
            request.payment_day_of_month,
        )

        settlement = Settlement(request.creditor, payments)
        self.repository.add_settlement(settlement)
        return settlement

    def remove_settlement(self, creditor: str) -> None:
        """Remove a settlement and all its payments."""
        self.repository.remove_settlement(creditor)

    @staticmethod
    def _generate_payment_schedule(
        creditor: str,
        total_amount: Decimal,
        monthly_payment: Decimal,
        first_due_date: date,
        payment_day_of_month: int | None = None,
    ) -> list[Payment]:
        """Generate a full payment schedule for a creditor."""
        payments: list[Payment] = []
        running_balance = total_amount
        payment_num = 1
        due_date = first_due_date

        while running_balance > Decimal("0.0001"):
            is_last = running_balance <= monthly_payment + Decimal("0.0001")

            if is_last:
                # Final payment: use remaining balance to avoid floating-point errors
                amount = running_balance
            else:
                amount = monthly_payment

            balance_before = running_balance
            balance_after = running_balance - amount

            payments.append(
                Payment(
                    creditor=creditor,
                    payment_num=payment_num,
                    amount=amount.quantize(Decimal("0.01")),
                    due_date=due_date,
                    balance_before=balance_before.quantize(Decimal("0.01")),
                    balance_after=balance_after.quantize(Decimal("0.01")),
                )
            )

            if is_last:
                break

            running_balance = balance_after
            payment_num += 1
            due_date = PaymentService._next_due_date(due_date, payment_day_of_month)

        return payments

    @staticmethod
    def _next_due_date(
        current: date, payment_day_of_month: int | None = None
    ) -> date:
        """Calculate the next due date."""
        if not payment_day_of_month:
            return current + timedelta(days=28)

        # Advance one calendar month, then set the day (clamped to last day of month)
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1

        last_day = calendar.monthrange(year, month)[1]
        day = min(payment_day_of_month, last_day)
        return date(year, month, day)

    @staticmethod
    def _payment_to_dto(payment: Payment) -> PaymentDTO:
        """Convert Payment entity to DTO."""
        return PaymentDTO(
            creditor=payment.creditor,
            payment_num=payment.payment_num,
            amount=payment.amount,
            due_date=payment.due_date,
            balance_before=payment.balance_before,
            balance_after=payment.balance_after,
            is_final=payment.is_final(),
            days_until_due=payment.days_until_due(),
        )

    @staticmethod
    def _settlement_to_summary(settlement: Settlement) -> SettlementSummaryDTO:
        """Convert Settlement entity to summary DTO."""
        next_payment = settlement.next_payment
        days_until = (
            next_payment.days_until_due() if next_payment else None
        )

        return SettlementSummaryDTO(
            creditor=settlement.creditor,
            next_due_date=settlement.next_due_date,
            next_amount=settlement.next_amount,
            current_balance=settlement.current_balance,
            payments_remaining=settlement.payments_remaining,
            total_remaining=settlement.total_remaining,
            paid_off=settlement.is_paid_off,
            days_until_due=days_until,
        )
