"""DTOs for payment and settlement data transfer."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import calendar as _calendar


@dataclass
class PaymentDTO:
    """Data Transfer Object for a single payment."""

    creditor: str
    payment_num: int
    amount: Decimal
    due_date: date
    balance_before: Decimal
    balance_after: Decimal
    is_final: bool
    days_until_due: int


@dataclass
class SettlementSummaryDTO:
    """Data Transfer Object for creditor summary on dashboard."""

    creditor: str
    next_due_date: date | None
    next_amount: Decimal | None
    current_balance: Decimal
    payments_remaining: int
    total_remaining: Decimal
    paid_off: bool
    days_until_due: int | None


@dataclass
class CreateSettlementRequestDTO:
    """Request DTO for creating a new settlement."""

    creditor: str
    total_amount: Decimal
    monthly_payment: Decimal
    first_due_date: date
    payment_day_of_month: int | None = None


@dataclass
class MonthlySummaryDTO:
    """Monthly summary for dashboard analytics."""

    year: int
    month: int
    total_due: Decimal
    total_paid: int

    @property
    def month_label(self) -> str:
        """Human-readable label like 'April 2026'."""
        return f"{_calendar.month_name[self.month]} {self.year}"
