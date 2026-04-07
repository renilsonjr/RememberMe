"""Flask application factory."""

import os
from flask import Flask

from src.infrastructure.repositories.excel_repository import ExcelRepository
from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter
from src.application.services.payment_service import PaymentService
from src.application.services.settlement_service import SettlementService
from src.application.services.calendar_service import CalendarService
from src.presentation.routes.dashboard_routes import create_dashboard_blueprint


class MockCalendarAdapter:
    """Mock calendar adapter for testing."""

    def create_event(self, payment, payments_remaining: int) -> str:
        """Return a mock event ID."""
        return f"mock-event-{payment.creditor}-{payment.payment_num}"

    def create_events(self, payments: list) -> list[str]:
        """Return mock event IDs."""
        if not payments:
            return []
        return [
            f"mock-event-{p.creditor}-{p.payment_num}"
            for p in payments
        ]


def create_app(config: dict | None = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dict to override defaults

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # Load configuration
    app.secret_key = os.environ.get("SECRET_KEY", "rememberme-dev-secret")
    if config:
        app.config.update(config)

    # Set default xlsx file path
    xlsx_file = app.config.get(
        "XLSX_FILE",
        os.path.join(os.path.dirname(__file__), "..", "..", "RememberMe.xlsx"),
    )
    app.config["XLSX_FILE"] = xlsx_file

    # Initialize infrastructure
    try:
        repository = ExcelRepository(xlsx_file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Configuration error: {exc}")

    # Calendar gateway requires credentials.json; fall back to mock if absent
    try:
        calendar_gateway = GoogleCalendarAdapter()
    except FileNotFoundError:
        calendar_gateway = MockCalendarAdapter()

    # Initialize services
    payment_service = PaymentService(repository)
    settlement_service = SettlementService(repository, payment_service)
    calendar_service = CalendarService(repository, calendar_gateway)

    # Register blueprints
    dashboard_bp = create_dashboard_blueprint(
        payment_service,
        settlement_service,
        calendar_service,
    )
    app.register_blueprint(dashboard_bp)

    return app


def create_app_with_config(xlsx_file: str, **kwargs) -> Flask:
    """Create app with specific Excel file and additional config."""
    config = {
        "XLSX_FILE": xlsx_file,
        **kwargs,
    }
    return create_app(config)
