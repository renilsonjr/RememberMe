import pytest
from datetime import date
from unittest.mock import MagicMock, patch, call
from calendar_events import create_calendar_events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PAYMENTS = [
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
        "due_date": date(2026, 5, 5),
        "balance_before": 800.0,
        "balance_after": 0.0,
    },
    {
        "creditor": "Credit Union B",
        "payment_num": 1,
        "amount": 150.0,
        "due_date": date(2026, 4, 1),
        "balance_before": 500.0,
        "balance_after": 350.0,
    },
]


def _make_service():
    """Return a mock Google Calendar service."""
    service = MagicMock()
    insert_mock = MagicMock()
    insert_mock.execute.return_value = {"id": "fake-event-id"}
    service.events.return_value.insert.return_value = insert_mock
    return service


def _get_inserted_body(service, call_index=0):
    """Extract the `body` kwarg passed to events().insert() for a given call."""
    return service.events.return_value.insert.call_args_list[call_index].kwargs["body"]


# ---------------------------------------------------------------------------
# 1. API insert called once per payment
# ---------------------------------------------------------------------------

class TestInsertCallCount:
    def test_called_once_per_payment(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        assert service.events.return_value.insert.call_count == len(SAMPLE_PAYMENTS)

    def test_execute_called_once_per_payment(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        insert_mock = service.events.return_value.insert.return_value
        assert insert_mock.execute.call_count == len(SAMPLE_PAYMENTS)

    def test_empty_payments_no_api_calls(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events([])
        service.events.return_value.insert.assert_not_called()

    def test_calendarid_is_primary(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        call_kwargs = service.events.return_value.insert.call_args.kwargs
        assert call_kwargs["calendarId"] == "primary"


# ---------------------------------------------------------------------------
# 2. Event title formatting
# ---------------------------------------------------------------------------

class TestEventTitle:
    def test_regular_payment_title(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        body = _get_inserted_body(service, call_index=0)
        assert body["summary"] == "Bank A — $200.00 due"

    def test_final_payment_title(self):
        """balance_after == 0 → title gets the ✅ prefix and FINAL PAYMENT label."""
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        # second payment for Bank A is the final one
        body = _get_inserted_body(service, call_index=1)
        assert body["summary"] == "✅ Bank A — FINAL PAYMENT $800.00"

    def test_regular_title_contains_amount(self):
        service = _make_service()
        payment = [{**SAMPLE_PAYMENTS[2]}]  # Credit Union B, $150
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(payment)
        body = _get_inserted_body(service, call_index=0)
        assert "$150.00" in body["summary"]

    def test_final_payment_does_not_have_regular_title_format(self):
        service = _make_service()
        final = [{**SAMPLE_PAYMENTS[1]}]  # balance_after == 0
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(final)
        body = _get_inserted_body(service)
        assert "due" not in body["summary"]
        assert "FINAL PAYMENT" in body["summary"]


# ---------------------------------------------------------------------------
# 3. Reminders
# ---------------------------------------------------------------------------

class TestReminders:
    def _get_reminders(self, service, call_index=0):
        body = _get_inserted_body(service, call_index)
        return body["reminders"]

    def test_reminders_use_override(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        reminders = self._get_reminders(service)
        assert reminders["useDefault"] is False

    def test_two_reminders_set(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        reminders = self._get_reminders(service)
        assert len(reminders["overrides"]) == 2

    def test_14_day_reminder_exists(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        overrides = self._get_reminders(service)["overrides"]
        minutes = [r["minutes"] for r in overrides]
        assert 14 * 24 * 60 in minutes

    def test_7_day_reminder_exists(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        overrides = self._get_reminders(service)["overrides"]
        minutes = [r["minutes"] for r in overrides]
        assert 7 * 24 * 60 in minutes

    def test_reminders_are_popup(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        overrides = self._get_reminders(service)["overrides"]
        assert all(r["method"] == "popup" for r in overrides)

    def test_reminders_present_on_final_payment(self):
        service = _make_service()
        final = [{**SAMPLE_PAYMENTS[1]}]
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(final)
        reminders = self._get_reminders(service)
        assert len(reminders["overrides"]) == 2


# ---------------------------------------------------------------------------
# 4. Description content
# ---------------------------------------------------------------------------

class TestDescription:
    def _get_description(self, service, call_index=0):
        return _get_inserted_body(service, call_index)["description"]

    def test_description_contains_payment_num(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        desc = self._get_description(service)
        assert "Payment #1" in desc

    def test_description_contains_balance_after(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        desc = self._get_description(service)
        assert "$800.00" in desc

    def test_description_balance_after_zero_for_final(self):
        service = _make_service()
        final = [{**SAMPLE_PAYMENTS[1]}]
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(final)
        desc = self._get_description(service)
        assert "$0.00" in desc

    def test_description_contains_payments_left(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        # Bank A has 2 payments; first one should show 1 payment left
        desc = self._get_description(service, call_index=0)
        assert "1 payment" in desc.lower()

    def test_description_zero_payments_left_for_final(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS)
        # second Bank A payment is final → 0 payments left
        desc = self._get_description(service, call_index=1)
        assert "0 payment" in desc.lower()

    def test_description_payments_left_for_single_creditor_group(self):
        service = _make_service()
        # Only Credit Union B — 1 payment, 0 remaining
        payment = [{**SAMPLE_PAYMENTS[2]}]
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(payment)
        desc = self._get_description(service)
        assert "0 payment" in desc.lower()


# ---------------------------------------------------------------------------
# 5. Event date
# ---------------------------------------------------------------------------

class TestEventDate:
    def test_start_date_matches_due_date(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        body = _get_inserted_body(service)
        assert body["start"]["date"] == "2026-04-05"

    def test_end_date_same_as_start(self):
        service = _make_service()
        with patch("calendar_events._build_service", return_value=service):
            create_calendar_events(SAMPLE_PAYMENTS[:1])
        body = _get_inserted_body(service)
        assert body["end"]["date"] == body["start"]["date"]
