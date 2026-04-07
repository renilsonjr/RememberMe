"""Payment domain entity."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Payment:
    """Immutable payment entity representing a single payment to a creditor."""

    creditor: str
    payment_num: int
    amount: Decimal
    due_date: date
    balance_before: Decimal
    balance_after: Decimal

    def is_final(self) -> bool:
        """Check if this is the final payment (balance reaches zero)."""
        return self.balance_after == Decimal("0")

    def is_due_soon(self, days: int) -> bool:
        """Check if payment is due within the specified number of days."""
        today = date.today()
        cutoff = today + timedelta(days=days)
        return today <= self.due_date <= cutoff

    def is_overdue(self) -> bool:
        """Check if payment is past due."""
        return self.due_date < date.today()

    def days_until_due(self) -> int:
        """Get number of days until this payment is due."""
        return (self.due_date - date.today()).days


@dataclass(frozen=True)
class Settlement:
    """A creditor's complete payment schedule (immutable)."""

    creditor: str
    payments: list[Payment]

    def __post_init__(self):
        """Validate settlement data."""
        if not self.creditor or not self.creditor.strip():
            raise ValueError("Creditor name cannot be empty")
        if not self.payments:
            raise ValueError("Settlement must have at least one payment")

    @property
    def is_paid_off(self) -> bool:
        """Check if all payments have been made (final balance is zero)."""
        return all(p.is_final() for p in self.payments)

    @property
    def next_payment(self) -> Payment | None:
        """Get the next payment due (first one on or after today)."""
        today = date.today()
        future = [p for p in self.payments if p.due_date >= today]
        return future[0] if future else None

    @property
    def next_due_date(self) -> date | None:
        """Get the date of the next payment."""
        next_p = self.next_payment
        return next_p.due_date if next_p else None

    @property
    def next_amount(self) -> Decimal | None:
        """Get the amount of the next payment."""
        next_p = self.next_payment
        return next_p.amount if next_p else None

    @property
    def current_balance(self) -> Decimal:
        """Get the current balance (balance before next payment)."""
        next_p = self.next_payment
        if next_p:
            return next_p.balance_before
        # If no future payments, return 0 (paid off)
        return Decimal("0") if self.payments else self.payments[-1].balance_after

    @property
    def payments_remaining(self) -> int:
        """Get count of remaining unpaid payments."""
        today = date.today()
        return len([p for p in self.payments if p.due_date >= today])

    @property
    def total_remaining(self) -> Decimal:
        """Get total amount remaining to be paid."""
        next_p = self.next_payment
        return next_p.balance_before if next_p else Decimal("0")

    def get_payments_due_soon(self, days: int) -> list[Payment]:
        """Get all payments due within N days."""
        return [p for p in self.payments if p.is_due_soon(days)]
