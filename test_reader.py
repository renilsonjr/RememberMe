import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from reader import load_payments, get_upcoming_payments, is_paid_off


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


# ---------------------------------------------------------------------------
# load_payments
# ---------------------------------------------------------------------------

class TestLoadPayments:
    def _make_wb(self, data_rows):
        """Build a minimal openpyxl workbook with 3 header rows + data_rows."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        # 3 header rows
        ws.append(["Settlement Tracker"])
        ws.append(["Generated: 2026-01-01"])
        ws.append(["Creditor", "Payment #", "Amount", "Due Date",
                   "Balance Before", "Balance After"])
        for row in data_rows:
            ws.append(row)
        return wb

    def test_returns_list(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        result = load_payments(str(path))
        assert isinstance(result, list)

    def test_skips_three_header_rows(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        result = load_payments(str(path))
        assert len(result) == 1

    def test_payment_dict_keys(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        row = load_payments(str(path))[0]
        assert set(row.keys()) == {
            "creditor", "payment_num", "amount",
            "due_date", "balance_before", "balance_after",
        }

    def test_values_parsed_correctly(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        row = load_payments(str(path))[0]
        assert row["creditor"] == "Bank A"
        assert row["payment_num"] == 1
        assert row["amount"] == 200.0
        assert row["due_date"] == date(2026, 4, 5)
        assert row["balance_before"] == 1000.0

    def test_balance_after_calculated_from_formula_cell(self, tmp_path):
        """balance_after column contains a formula (None when read); must be computed."""
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        row = load_payments(str(path))[0]
        assert row["balance_after"] == pytest.approx(800.0)

    def test_blank_rows_ignored(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
            [None, None, None, None, None, None],   # blank separator row
            ["Credit Union B", 1, 150.0, date(2026, 4, 1), 500.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        result = load_payments(str(path))
        assert len(result) == 2

    def test_multiple_payments_same_creditor(self, tmp_path):
        wb = self._make_wb([
            ["Bank A", 1, 200.0, date(2026, 4, 5), 1000.0, None],
            ["Bank A", 2, 800.0, date(2026, 5, 5), 800.0, None],
        ])
        path = tmp_path / "test.xlsx"
        wb.save(path)
        result = load_payments(str(path))
        assert len(result) == 2
        assert result[1]["balance_after"] == pytest.approx(0.0)

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_payments("/nonexistent/path/file.xlsx")


# ---------------------------------------------------------------------------
# get_upcoming_payments
# ---------------------------------------------------------------------------

class TestGetUpcomingPayments:
    def test_returns_payments_within_window(self):
        today = date.today()
        payments = [
            {**SAMPLE_PAYMENTS[0], "due_date": today + timedelta(days=7)},
            {**SAMPLE_PAYMENTS[1], "due_date": today + timedelta(days=30)},
        ]
        result = get_upcoming_payments(payments, days=14)
        assert len(result) == 1
        assert result[0]["due_date"] == today + timedelta(days=7)

    def test_includes_today(self):
        today = date.today()
        payments = [{**SAMPLE_PAYMENTS[0], "due_date": today}]
        result = get_upcoming_payments(payments, days=14)
        assert len(result) == 1

    def test_includes_boundary_day(self):
        today = date.today()
        payments = [{**SAMPLE_PAYMENTS[0], "due_date": today + timedelta(days=14)}]
        result = get_upcoming_payments(payments, days=14)
        assert len(result) == 1

    def test_excludes_past_payments(self):
        today = date.today()
        payments = [{**SAMPLE_PAYMENTS[0], "due_date": today - timedelta(days=1)}]
        result = get_upcoming_payments(payments, days=14)
        assert len(result) == 0

    def test_excludes_payments_beyond_window(self):
        today = date.today()
        payments = [{**SAMPLE_PAYMENTS[0], "due_date": today + timedelta(days=15)}]
        result = get_upcoming_payments(payments, days=14)
        assert len(result) == 0

    def test_default_window_is_14_days(self):
        today = date.today()
        payments = [{**SAMPLE_PAYMENTS[0], "due_date": today + timedelta(days=10)}]
        result = get_upcoming_payments(payments)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        assert get_upcoming_payments([]) == []

    def test_custom_window(self):
        today = date.today()
        payments = [
            {**SAMPLE_PAYMENTS[0], "due_date": today + timedelta(days=3)},
            {**SAMPLE_PAYMENTS[1], "due_date": today + timedelta(days=10)},
        ]
        result = get_upcoming_payments(payments, days=7)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# is_paid_off
# ---------------------------------------------------------------------------

class TestIsPaidOff:
    def test_returns_true_when_last_balance_after_is_zero(self):
        assert is_paid_off(SAMPLE_PAYMENTS, "Bank A") is True

    def test_returns_false_when_last_balance_after_nonzero(self):
        assert is_paid_off(SAMPLE_PAYMENTS, "Credit Union B") is False

    def test_unknown_creditor_raises(self):
        with pytest.raises(ValueError):
            is_paid_off(SAMPLE_PAYMENTS, "Unknown Creditor")

    def test_uses_last_payment_not_first(self):
        payments = [
            {**SAMPLE_PAYMENTS[0], "balance_after": 0.0},   # first — paid off
            {**SAMPLE_PAYMENTS[1], "balance_after": 100.0}, # last — still owes
        ]
        # Both are "Bank A"; last payment balance_after is 100 → not paid off
        assert is_paid_off(payments, "Bank A") is False

    def test_single_payment_paid_off(self):
        payments = [
            {
                "creditor": "Store Card",
                "payment_num": 1,
                "amount": 500.0,
                "due_date": date(2026, 4, 1),
                "balance_before": 500.0,
                "balance_after": 0.0,
            }
        ]
        assert is_paid_off(payments, "Store Card") is True
