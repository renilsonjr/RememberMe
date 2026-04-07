"""Dashboard routes."""

from datetime import datetime
from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.application.dto.payment_dto import CreateSettlementRequestDTO
from src.application.services.payment_service import PaymentService
from src.application.services.settlement_service import SettlementService
from src.application.services.calendar_service import CalendarService
from src.domain.errors import SettlementError


def create_dashboard_blueprint(
    payment_service: PaymentService,
    settlement_service: SettlementService,
    calendar_service: CalendarService,
) -> Blueprint:
    """Create the dashboard blueprint with all routes."""
    bp = Blueprint("dashboard", __name__)

    @bp.route("/")
    def index():
        """Render the main dashboard."""
        summaries = payment_service.get_all_summaries()
        monthly = payment_service.get_monthly_summary()
        return render_template(
            "index.html",
            summaries=summaries,
            monthly=monthly,
        )

    @bp.route("/add-settlement", methods=["POST"])
    def add_settlement():
        """Create a new settlement with auto-generated payment schedule."""
        creditor_name = request.form.get("creditor_name", "").strip()
        total_amount_str = request.form.get("total_amount", "").strip()
        monthly_payment_str = request.form.get("monthly_payment", "").strip()
        first_due_date_str = request.form.get("first_due_date", "").strip()
        payment_day_str = request.form.get("payment_day_of_month", "").strip()

        # Validate required fields
        if not creditor_name:
            flash("Missing creditor name", "error")
            return redirect(url_for("dashboard.index"))

        try:
            total_amount = float(total_amount_str)
            monthly_payment = float(monthly_payment_str)
        except ValueError:
            flash("Invalid amount format", "error")
            return redirect(url_for("dashboard.index"))

        try:
            first_due_date = datetime.strptime(first_due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format, expected YYYY-MM-DD", "error")
            return redirect(url_for("dashboard.index"))

        payment_day = int(payment_day_str) if payment_day_str.isdigit() else None

        try:
            settlement = settlement_service.add_settlement(
                creditor=creditor_name,
                total_amount=total_amount,
                monthly_payment=monthly_payment,
                first_due_date=first_due_date,
                payment_day_of_month=payment_day,
            )
            num_payments = len(payment_service.get_all_payments())
            flash(
                f"Added settlement for {creditor_name} with {num_payments} total payments.",
                "success",
            )
        except SettlementError as exc:
            flash(f"Failed to add settlement: {exc}", "error")

        return redirect(url_for("dashboard.index"))

    @bp.route("/delete-settlement", methods=["POST"])
    def delete_settlement():
        """Delete a settlement and all its payments."""
        creditor_name = request.form.get("creditor_name", "").strip()

        if not creditor_name:
            flash("Missing creditor name", "error")
            return redirect(url_for("dashboard.index"))

        try:
            settlement_service.delete_settlement(creditor_name)
            flash(f"Removed all payments for {creditor_name}.", "success")
        except SettlementError as exc:
            flash(str(exc), "error")

        return redirect(url_for("dashboard.index"))

    @bp.route("/sync")
    def sync():
        """Sync upcoming payments to Google Calendar."""
        try:
            event_ids = calendar_service.sync_upcoming_payments(days=14)
            message = f"{len(event_ids)} calendar event(s) created successfully."
            status = "success"
        except Exception as exc:
            message = f"Error syncing to Google Calendar: {exc}"
            status = "error"

        return render_template("sync.html", message=message, status=status)

    return bp
