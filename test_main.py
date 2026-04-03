import pytest
from datetime import date
from unittest.mock import patch, call
import main as main_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UPCOMING = [
    {
        "creditor": "Bank A",
        "payment_num": 1,
        "amount": 200.0,
        "due_date": date(2026, 4, 5),
        "balance_before": 1000.0,
        "balance_after": 800.0,
    },
    {
        "creditor": "Bank A",
        "payment_num": 2,
        "amount": 800.0,
        "due_date": date(2026, 4, 10),
        "balance_before": 800.0,
        "balance_after": 0.0,
    },
]

ALL_PAYMENTS = UPCOMING + [
    {
        "creditor": "Credit Union B",
        "payment_num": 1,
        "amount": 150.0,
        "due_date": date(2026, 6, 1),   # beyond 14-day window
        "balance_before": 500.0,
        "balance_after": 350.0,
    },
]


# ---------------------------------------------------------------------------
# load_payments is called
# ---------------------------------------------------------------------------

class TestLoadPayments:
    def test_load_payments_called_with_xlsx(self, capsys):
        with patch("main.load_payments", return_value=[]) as mock_load, \
             patch("main.get_upcoming_payments", return_value=[]), \
             patch("main.create_calendar_events", return_value=[]):
            main_module.run()
        mock_load.assert_called_once()
        assert mock_load.call_args.args[0].endswith("settlement_tracker.xlsx")

    def test_load_payments_result_passed_to_upcoming(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS) as mock_load, \
             patch("main.get_upcoming_payments", return_value=[]) as mock_upcoming, \
             patch("main.create_calendar_events", return_value=[]):
            main_module.run()
        mock_upcoming.assert_called_once_with(ALL_PAYMENTS, days=14)


# ---------------------------------------------------------------------------
# create_calendar_events is called correctly
# ---------------------------------------------------------------------------

class TestCreateCalendarEvents:
    def test_called_with_upcoming_payments(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]) as mock_create:
            main_module.run()
        mock_create.assert_called_once_with(UPCOMING, all_payments=ALL_PAYMENTS)

    def test_not_called_when_no_upcoming(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=[]), \
             patch("main.create_calendar_events") as mock_create:
            main_module.run()
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# Terminal summary output
# ---------------------------------------------------------------------------

class TestSummaryOutput:
    def test_prints_creditor(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "Bank A" in out

    def test_prints_amount(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "$200.00" in out

    def test_prints_due_date(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "2026-04-05" in out

    def test_prints_balance_after(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "$800.00" in out

    def test_marks_final_payment(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "FINAL" in out.upper()

    def test_prints_one_line_per_payment(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        # Both upcoming payments should appear
        assert "Bank A" in out
        assert "$200.00" in out
        assert "$800.00" in out


# ---------------------------------------------------------------------------
# No upcoming payments case
# ---------------------------------------------------------------------------

class TestNoUpcomingPayments:
    def test_prints_no_payments_message(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=[]), \
             patch("main.create_calendar_events", return_value=[]):
            main_module.run()
        out = capsys.readouterr().out
        assert "No payments due in the next 14 days" in out

    def test_no_payments_message_not_shown_when_there_are_payments(self, capsys):
        with patch("main.load_payments", return_value=ALL_PAYMENTS), \
             patch("main.get_upcoming_payments", return_value=UPCOMING), \
             patch("main.create_calendar_events", return_value=["id1", "id2"]):
            main_module.run()
        out = capsys.readouterr().out
        assert "No payments due" not in out
