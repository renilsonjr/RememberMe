"""Integration tests for Flask dashboard routes."""

from datetime import date
from decimal import Decimal

import pytest

from src.presentation.app import create_app
from src.domain.payment import Payment, Settlement


@pytest.fixture
def app(temp_excel_file):
    """Create a Flask app for testing."""
    app = create_app({"XLSX_FILE": temp_excel_file, "TESTING": True})
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestDashboardRoutes:
    """Tests for dashboard routes."""

    def test_index_route(self, client):
        """Test GET /."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"RememberMe" in response.data or b"creditor" in response.data.lower()

    def test_add_settlement_missing_field(self, client):
        """Test POST /add-settlement with missing field."""
        response = client.post(
            "/add-settlement",
            data={"creditor_name": "TEST"},
        )
        assert response.status_code == 302  # Redirect

    def test_add_settlement_invalid_amount(self, client):
        """Test POST /add-settlement with invalid amount."""
        response = client.post(
            "/add-settlement",
            data={
                "creditor_name": "TEST",
                "total_amount": "invalid",
                "monthly_payment": "100",
                "first_due_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 302  # Redirect

    def test_add_settlement_invalid_date(self, client):
        """Test POST /add-settlement with invalid date."""
        response = client.post(
            "/add-settlement",
            data={
                "creditor_name": "TEST",
                "total_amount": "500",
                "monthly_payment": "100",
                "first_due_date": "invalid-date",
            },
        )
        assert response.status_code == 302  # Redirect

    def test_delete_settlement_missing_name(self, client):
        """Test POST /delete-settlement with missing name."""
        response = client.post(
            "/delete-settlement",
            data={},
        )
        assert response.status_code == 302  # Redirect

    def test_delete_settlement_not_found(self, client):
        """Test POST /delete-settlement with non-existent creditor."""
        response = client.post(
            "/delete-settlement",
            data={"creditor_name": "NONEXISTENT"},
        )
        assert response.status_code == 302  # Redirect

    def test_sync_route(self, client):
        """Test GET /sync."""
        response = client.get("/sync")
        assert response.status_code == 200
        assert b"sync" in response.data.lower() or b"calendar" in response.data.lower()
