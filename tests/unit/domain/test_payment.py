"""Tests for Payment and Settlement domain entities."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.domain.payment import Payment, Settlement
from src.domain.errors import InvalidPaymentError


class TestPayment:
    """Tests for Payment entity."""

    def test_payment_creation(self):
        """Test creating a payment."""
        payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        assert payment.creditor == "TEST"
        assert payment.payment_num == 1
        assert payment.amount == Decimal("100.00")

    def test_payment_is_immutable(self):
        """Test that Payment is immutable."""
        payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        with pytest.raises(AttributeError):
            payment.amount = Decimal("200.00")

    def test_is_final(self):
        """Test is_final method."""
        final_payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("0.00"),
        )

        not_final = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        assert final_payment.is_final() is True
        assert not_final.is_final() is False

    def test_is_due_soon(self):
        """Test is_due_soon method."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        next_month = today + timedelta(days=30)

        payment_tomorrow = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=tomorrow,
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        payment_next_month = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=next_month,
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        assert payment_tomorrow.is_due_soon(7) is True
        assert payment_next_month.is_due_soon(14) is False

    def test_days_until_due(self):
        """Test days_until_due method."""
        today = date.today()
        payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=today + timedelta(days=5),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        assert payment.days_until_due() == 5


class TestSettlement:
    """Tests for Settlement entity."""

    def test_settlement_creation(self):
        """Test creating a settlement."""
        payments = [
            Payment(
                creditor="TEST",
                payment_num=1,
                amount=Decimal("100.00"),
                due_date=date.today(),
                balance_before=Decimal("300.00"),
                balance_after=Decimal("200.00"),
            ),
        ]

        settlement = Settlement("TEST", payments)

        assert settlement.creditor == "TEST"
        assert len(settlement.payments) == 1

    def test_settlement_validates_empty_creditor(self):
        """Test that settlement validates creditor name."""
        payments = [
            Payment(
                creditor="TEST",
                payment_num=1,
                amount=Decimal("100.00"),
                due_date=date.today(),
                balance_before=Decimal("100.00"),
                balance_after=Decimal("0.00"),
            ),
        ]

        with pytest.raises(ValueError):
            Settlement("", payments)

    def test_settlement_validates_empty_payments(self):
        """Test that settlement requires at least one payment."""
        with pytest.raises(ValueError):
            Settlement("TEST", [])

    def test_is_paid_off(self):
        """Test is_paid_off property."""
        final_payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("0.00"),
        )

        paid_off_settlement = Settlement("TEST", [final_payment])
        assert paid_off_settlement.is_paid_off is True

        not_final_payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        active_settlement = Settlement("TEST", [not_final_payment])
        assert active_settlement.is_paid_off is False

    def test_next_payment(self):
        """Test next_payment property."""
        today = date.today()
        payments = [
            Payment(
                creditor="TEST",
                payment_num=1,
                amount=Decimal("100.00"),
                due_date=today - timedelta(days=10),  # Past due
                balance_before=Decimal("300.00"),
                balance_after=Decimal("200.00"),
            ),
            Payment(
                creditor="TEST",
                payment_num=2,
                amount=Decimal("100.00"),
                due_date=today + timedelta(days=5),  # Future
                balance_before=Decimal("200.00"),
                balance_after=Decimal("100.00"),
            ),
            Payment(
                creditor="TEST",
                payment_num=3,
                amount=Decimal("100.00"),
                due_date=today + timedelta(days=15),  # Further future
                balance_before=Decimal("100.00"),
                balance_after=Decimal("0.00"),
            ),
        ]

        settlement = Settlement("TEST", payments)
        next_payment = settlement.next_payment

        assert next_payment is not None
        assert next_payment.payment_num == 2

    def test_payments_remaining(self):
        """Test payments_remaining property."""
        today = date.today()
        payments = [
            Payment(
                creditor="TEST",
                payment_num=1,
                amount=Decimal("100.00"),
                due_date=today - timedelta(days=10),
                balance_before=Decimal("300.00"),
                balance_after=Decimal("200.00"),
            ),
            Payment(
                creditor="TEST",
                payment_num=2,
                amount=Decimal("100.00"),
                due_date=today + timedelta(days=5),
                balance_before=Decimal("200.00"),
                balance_after=Decimal("100.00"),
            ),
            Payment(
                creditor="TEST",
                payment_num=3,
                amount=Decimal("100.00"),
                due_date=today + timedelta(days=15),
                balance_before=Decimal("100.00"),
                balance_after=Decimal("0.00"),
            ),
        ]

        settlement = Settlement("TEST", payments)

        assert settlement.payments_remaining == 2
