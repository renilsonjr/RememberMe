"""Tests for PaymentService."""

from datetime import date
from decimal import Decimal

import pytest

from src.application.services.payment_service import PaymentService
from src.domain.payment import Payment, Settlement


class MockRepository:
    """Mock repository for testing."""

    def __init__(self):
        self.payments = []
        self.settlements = {}

    def get_all_payments(self):
        return self.payments

    def get_all_settlements(self):
        settlements_dict = {}
        for p in self.payments:
            if p.creditor not in settlements_dict:
                settlements_dict[p.creditor] = []
            settlements_dict[p.creditor].append(p)
        return [
            Settlement(creditor, payments)
            for creditor, payments in settlements_dict.items()
        ]

    def get_settlement(self, creditor):
        settlements = self.get_all_settlements()
        for s in settlements:
            if s.creditor == creditor:
                return s
        return None

    def add_settlement(self, settlement):
        self.payments.extend(settlement.payments)
        self.settlements[settlement.creditor] = settlement

    def remove_settlement(self, creditor):
        self.payments = [p for p in self.payments if p.creditor != creditor]
        if creditor in self.settlements:
            del self.settlements[creditor]

    def update_settlement(self, settlement):
        self.remove_settlement(settlement.creditor)
        self.add_settlement(settlement)


class TestPaymentService:
    """Tests for PaymentService."""

    def test_service_initialization(self):
        """Test creating a payment service."""
        repo = MockRepository()
        service = PaymentService(repo)

        assert service.repository is repo

    def test_get_all_payments(self):
        """Test getting all payments."""
        repo = MockRepository()
        payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )
        repo.payments = [payment]

        service = PaymentService(repo)
        payments = service.get_all_payments()

        assert len(payments) == 1
        assert payments[0].creditor == "TEST"

    def test_get_upcoming_payments(self):
        """Test getting upcoming payments."""
        from datetime import timedelta

        repo = MockRepository()
        today = date.today()

        past_payment = Payment(
            creditor="TEST1",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=today - timedelta(days=10),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        upcoming_payment = Payment(
            creditor="TEST2",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=today + timedelta(days=5),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        future_payment = Payment(
            creditor="TEST3",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=today + timedelta(days=30),
            balance_before=Decimal("500.00"),
            balance_after=Decimal("400.00"),
        )

        repo.payments = [past_payment, upcoming_payment, future_payment]

        service = PaymentService(repo)
        upcoming = service.get_upcoming_payments(days=14)

        assert len(upcoming) == 1
        assert upcoming[0].creditor == "TEST2"

    def test_create_settlement(self):
        """Test creating a settlement with payment schedule."""
        from src.application.dto.payment_dto import CreateSettlementRequestDTO

        repo = MockRepository()
        service = PaymentService(repo)

        request = CreateSettlementRequestDTO(
            creditor="NEW",
            total_amount=Decimal("300.00"),
            monthly_payment=Decimal("100.00"),
            first_due_date=date.today(),
            payment_day_of_month=None,
        )

        settlement = service.create_settlement(request)

        assert settlement.creditor == "NEW"
        assert len(settlement.payments) == 3
        assert settlement.payments[0].amount == Decimal("100.00")
        assert settlement.payments[-1].is_final()

    def test_remove_settlement(self):
        """Test removing a settlement."""
        repo = MockRepository()
        payment = Payment(
            creditor="TEST",
            payment_num=1,
            amount=Decimal("100.00"),
            due_date=date.today(),
            balance_before=Decimal("100.00"),
            balance_after=Decimal("0.00"),
        )
        settlement = Settlement("TEST", [payment])
        repo.add_settlement(settlement)

        service = PaymentService(repo)
        service.remove_settlement("TEST")

        assert len(repo.payments) == 0
