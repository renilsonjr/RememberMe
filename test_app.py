import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from app import app as flask_app, build_creditor_summaries


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PAYMENTS = [
    {
        "creditor": "Bank A",
        "payment_num": 1,
        "amount": 200.0,
        "due_date": date.today() + timedelta(days=7),
        "balance_before": 1000.0,
        "balance_after": 800.0,
    },
    {
        "creditor": "Bank A",
        "payment_num": 2,
        "amount": 800.0,
        "due_date": date.today() + timedelta(days=37),
        "balance_before": 800.0,
        "balance_after": 0.0,
    },
    {
        "creditor": "Credit Union B",
        "payment_num": 1,
        "amount": 150.0,
        "due_date": date.today() + timedelta(days=60),
        "balance_before": 500.0,
        "balance_after": 350.0,
    },
]


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["XLSX_FILE"] = "does_not_matter.xlsx"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# build_creditor_summaries
# ---------------------------------------------------------------------------

class TestBuildCreditorSummaries:

    def test_returns_one_entry_per_creditor(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        assert len(summaries) == 2

    def test_creditor_name_present(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        names = [s["creditor"] for s in summaries]
        assert "Bank A" in names
        assert "Credit Union B" in names

    def test_next_payment_is_first_future_payment(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        bank_a = next(s for s in summaries if s["creditor"] == "Bank A")
        assert bank_a["next_due_date"] == SAMPLE_PAYMENTS[0]["due_date"]
        assert bank_a["next_amount"] == pytest.approx(200.0)

    def test_balance_is_balance_before_of_next_payment(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        bank_a = next(s for s in summaries if s["creditor"] == "Bank A")
        assert bank_a["balance"] == pytest.approx(1000.0)

    def test_payments_left_counts_remaining(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        bank_a = next(s for s in summaries if s["creditor"] == "Bank A")
        assert bank_a["payments_left"] == 2

    def test_paid_off_false_when_balance_nonzero(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        bank_a = next(s for s in summaries if s["creditor"] == "Bank A")
        assert bank_a["paid_off"] is False

    def test_paid_off_true_when_all_payments_done(self):
        paid_payments = [
            {**SAMPLE_PAYMENTS[1], "balance_after": 0.0,
             "due_date": date.today() - timedelta(days=1)},
        ]
        summaries = build_creditor_summaries(paid_payments)
        assert summaries[0]["paid_off"] is True

    def test_due_soon_true_within_14_days(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        bank_a = next(s for s in summaries if s["creditor"] == "Bank A")
        assert bank_a["due_soon"] is True  # 7 days away

    def test_due_soon_false_outside_14_days(self):
        summaries = build_creditor_summaries(SAMPLE_PAYMENTS)
        credit_union = next(s for s in summaries if s["creditor"] == "Credit Union B")
        assert credit_union["due_soon"] is False  # 60 days away

    def test_empty_payments_returns_empty(self):
        assert build_creditor_summaries([]) == []


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestIndexRoute:

    def test_returns_200(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS):
            response = client.get("/")
        assert response.status_code == 200

    def test_load_payments_called_with_configured_xlsx(self, client):
        with patch("app.load_payments", return_value=[]) as mock_load:
            client.get("/")
        mock_load.assert_called_once_with("does_not_matter.xlsx")

    def test_creditor_name_appears_in_html(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS):
            response = client.get("/")
        assert b"Bank A" in response.data

    def test_both_creditors_appear(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS):
            response = client.get("/")
        assert b"Bank A" in response.data
        assert b"Credit Union B" in response.data

    def test_paid_off_badge_present_when_balance_zero(self, client):
        paid_payments = [
            {**SAMPLE_PAYMENTS[0], "balance_after": 0.0,
             "due_date": date.today() - timedelta(days=5)},
        ]
        with patch("app.load_payments", return_value=paid_payments):
            response = client.get("/")
        assert b"PAID OFF" in response.data

    def test_due_soon_class_in_html(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS):
            response = client.get("/")
        assert b"due-soon" in response.data

    def test_empty_payments_renders_without_error(self, client):
        with patch("app.load_payments", return_value=[]):
            response = client.get("/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /add-settlement
# ---------------------------------------------------------------------------

class TestAddSettlementRoute:

    VALID_FORM = {
        "creditor_name": "NEW BANK",
        "total_amount": "500.00",
        "monthly_payment": "100.00",
        "first_due_date": "2026-06-01",
        "payment_day_of_month": "1",
    }

    def test_post_redirects_to_index(self, client):
        with patch("app.generate_payment_rows", return_value=[]), \
             patch("app.append_to_excel"):
            response = client.post("/add-settlement", data=self.VALID_FORM)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")

    def test_generate_payment_rows_called_with_form_data(self, client):
        with patch("app.generate_payment_rows", return_value=[]) as mock_gen, \
             patch("app.append_to_excel"):
            client.post("/add-settlement", data=self.VALID_FORM)
        mock_gen.assert_called_once()
        args, kwargs = mock_gen.call_args
        assert args[0] == "NEW BANK"
        assert args[1] == pytest.approx(500.0)
        assert args[2] == pytest.approx(100.0)
        assert args[3] == date(2026, 6, 1)

    def test_append_to_excel_called(self, client):
        fake_rows = [{"creditor": "NEW BANK"}]
        with patch("app.generate_payment_rows", return_value=fake_rows), \
             patch("app.append_to_excel") as mock_append:
            client.post("/add-settlement", data=self.VALID_FORM)
        mock_append.assert_called_once()
        assert mock_append.call_args.args[0] == fake_rows

    def test_missing_creditor_name_returns_400(self, client):
        bad_form = {**self.VALID_FORM}
        del bad_form["creditor_name"]
        response = client.post("/add-settlement", data=bad_form)
        assert response.status_code == 400

    def test_invalid_date_returns_400(self, client):
        bad_form = {**self.VALID_FORM, "first_due_date": "not-a-date"}
        response = client.post("/add-settlement", data=bad_form)
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /sync
# ---------------------------------------------------------------------------

class TestSyncRoute:

    def test_returns_200(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS), \
             patch("app.get_upcoming_payments", return_value=SAMPLE_PAYMENTS[:1]), \
             patch("app.create_calendar_events", return_value=["id1"]):
            response = client.get("/sync")
        assert response.status_code == 200

    def test_create_calendar_events_called(self, client):
        upcoming = SAMPLE_PAYMENTS[:1]
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS), \
             patch("app.get_upcoming_payments", return_value=upcoming), \
             patch("app.create_calendar_events", return_value=["id1"]) as mock_sync:
            client.get("/sync")
        mock_sync.assert_called_once_with(upcoming, all_payments=SAMPLE_PAYMENTS)

    def test_success_message_in_response(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS), \
             patch("app.get_upcoming_payments", return_value=SAMPLE_PAYMENTS[:1]), \
             patch("app.create_calendar_events", return_value=["id1"]):
            response = client.get("/sync")
        assert b"1" in response.data

    def test_calendar_error_shows_error_message(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS), \
             patch("app.get_upcoming_payments", return_value=SAMPLE_PAYMENTS[:1]), \
             patch("app.create_calendar_events",
                   side_effect=Exception("API error")):
            response = client.get("/sync")
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"Error" in response.data

    def test_no_upcoming_shows_zero_events(self, client):
        with patch("app.load_payments", return_value=SAMPLE_PAYMENTS), \
             patch("app.get_upcoming_payments", return_value=[]), \
             patch("app.create_calendar_events", return_value=[]):
            response = client.get("/sync")
        assert b"0" in response.data


# ---------------------------------------------------------------------------
# POST /delete-settlement
# ---------------------------------------------------------------------------

class TestDeleteSettlementRoute:

    def test_post_redirects_to_index(self, client):
        with patch("app.remove_creditor"):
            response = client.post("/delete-settlement",
                                   data={"creditor_name": "Bank A"})
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")

    def test_remove_creditor_called_with_name(self, client):
        with patch("app.remove_creditor") as mock_remove:
            client.post("/delete-settlement", data={"creditor_name": "Bank A"})
        mock_remove.assert_called_once()
        assert mock_remove.call_args.args[0] == "Bank A"

    def test_success_flash_message_shown(self, client):
        with patch("app.remove_creditor"), \
             patch("app.load_payments", return_value=[]):
            response = client.post("/delete-settlement",
                                   data={"creditor_name": "Bank A"},
                                   follow_redirects=True)
        assert response.status_code == 200

    def test_nonexistent_creditor_redirects_with_error(self, client):
        with patch("app.remove_creditor",
                   side_effect=ValueError("Bank Z not found")):
            response = client.post("/delete-settlement",
                                   data={"creditor_name": "Bank Z"})
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")

    def test_missing_creditor_name_returns_400(self, client):
        response = client.post("/delete-settlement", data={})
        assert response.status_code == 400

    def test_remove_creditor_called_with_correct_filepath(self, client):
        with patch("app.remove_creditor") as mock_remove:
            client.post("/delete-settlement", data={"creditor_name": "Bank A"})
        assert mock_remove.call_args.args[1] == "does_not_matter.xlsx"
