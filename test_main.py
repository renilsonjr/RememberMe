import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock, call
import main as main_module

from src.application.dto.payment_dto import PaymentDTO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payment_dto(creditor, num, amount, due_date, balance_after, is_final=False):
    return PaymentDTO(
        creditor=creditor,
        payment_num=num,
        amount=Decimal(str(amount)),
        due_date=due_date,
        balance_before=Decimal("1000.00"),
        balance_after=Decimal(str(balance_after)),
        is_final=is_final,
        days_until_due=5,
    )


UPCOMING = [
    _make_payment_dto("Bank A", 1, 200.0, date(2026, 4, 5), 800.0),
    _make_payment_dto("Bank A", 2, 800.0, date(2026, 4, 10), 0.0, is_final=True),
]


# ---------------------------------------------------------------------------
# Terminal output tests — mock PaymentService and CalendarService
# ---------------------------------------------------------------------------

class TestSummaryOutput:

    def _run_main(self):
        """Run main() with mocked services."""
        mock_payment_service = MagicMock()
        mock_payment_service.get_upcoming_payments.return_value = UPCOMING

        mock_calendar_service = MagicMock()
        mock_calendar_service.sync_upcoming_payments.return_value = ["id1", "id2"]

        with patch("main.ExcelRepository"), \
             patch("main.GoogleCalendarAdapter"), \
             patch("main.PaymentService", return_value=mock_payment_service), \
             patch("main.CalendarService", return_value=mock_calendar_service):
            main_module.main()

    def test_prints_creditor(self, capsys):
        self._run_main()
        assert "Bank A" in capsys.readouterr().out

    def test_prints_amount(self, capsys):
        self._run_main()
        assert "200.00" in capsys.readouterr().out

    def test_prints_due_date(self, capsys):
        self._run_main()
        assert "2026-04-05" in capsys.readouterr().out

    def test_prints_balance_after(self, capsys):
        self._run_main()
        assert "800.00" in capsys.readouterr().out

    def test_marks_final_payment(self, capsys):
        self._run_main()
        assert "FINAL" in capsys.readouterr().out.upper()

    def test_prints_one_line_per_payment(self, capsys):
        self._run_main()
        out = capsys.readouterr().out
        assert "200.00" in out
        assert "800.00" in out


# ---------------------------------------------------------------------------
# No upcoming payments
# ---------------------------------------------------------------------------

class TestNoUpcomingPayments:

    def _run_with_empty(self):
        mock_payment_service = MagicMock()
        mock_payment_service.get_upcoming_payments.return_value = []

        mock_calendar_service = MagicMock()

        with patch("main.ExcelRepository"), \
             patch("main.GoogleCalendarAdapter"), \
             patch("main.PaymentService", return_value=mock_payment_service), \
             patch("main.CalendarService", return_value=mock_calendar_service):
            main_module.main()

        return mock_calendar_service

    def test_prints_no_payments_message(self, capsys):
        self._run_with_empty()
        assert "No payments due in the next 14 days" in capsys.readouterr().out

    def test_calendar_not_called_when_no_upcoming(self, capsys):
        mock_calendar = self._run_with_empty()
        mock_calendar.sync_upcoming_payments.assert_not_called()

    def test_no_payments_message_not_shown_when_there_are_payments(self, capsys):
        mock_payment_service = MagicMock()
        mock_payment_service.get_upcoming_payments.return_value = UPCOMING

        mock_calendar_service = MagicMock()
        mock_calendar_service.sync_upcoming_payments.return_value = ["id1"]

        with patch("main.ExcelRepository"), \
             patch("main.GoogleCalendarAdapter"), \
             patch("main.PaymentService", return_value=mock_payment_service), \
             patch("main.CalendarService", return_value=mock_calendar_service):
            main_module.main()

        assert "No payments due" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Service wiring
# ---------------------------------------------------------------------------

class TestServiceWiring:

    def test_payment_service_called_with_14_days(self):
        mock_payment_service = MagicMock()
        mock_payment_service.get_upcoming_payments.return_value = []

        with patch("main.ExcelRepository"), \
             patch("main.GoogleCalendarAdapter"), \
             patch("main.PaymentService", return_value=mock_payment_service), \
             patch("main.CalendarService"):
            main_module.main()

        mock_payment_service.get_upcoming_payments.assert_called_once_with(days=14)

    def test_calendar_sync_called_when_upcoming_exist(self):
        mock_payment_service = MagicMock()
        mock_payment_service.get_upcoming_payments.return_value = UPCOMING

        mock_calendar_service = MagicMock()
        mock_calendar_service.sync_upcoming_payments.return_value = ["id1", "id2"]

        with patch("main.ExcelRepository"), \
             patch("main.GoogleCalendarAdapter"), \
             patch("main.PaymentService", return_value=mock_payment_service), \
             patch("main.CalendarService", return_value=mock_calendar_service):
            main_module.main()

        mock_calendar_service.sync_upcoming_payments.assert_called_once_with(days=14)
