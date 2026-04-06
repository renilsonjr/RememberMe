# Run with: python3 app.py

import os
from datetime import date, datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash

from reader import load_payments, get_upcoming_payments, get_monthly_summary
from calendar_events import create_calendar_events
from excel_writer import generate_payment_rows, append_to_excel, remove_creditor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rememberme-dev-secret")
app.config.setdefault("XLSX_FILE",
    os.path.join(os.path.dirname(__file__), "RememberMe.xlsx"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_creditor_summaries(payments: list[dict]) -> list[dict]:
    """
    Aggregate the full payment list into one summary dict per creditor,
    suitable for rendering the dashboard table.
    """
    if not payments:
        return []

    today = date.today()
    cutoff = today + timedelta(days=14)

    # Preserve insertion order of creditors
    seen: dict[str, list[dict]] = {}
    for p in payments:
        seen.setdefault(p["creditor"], []).append(p)

    summaries = []
    for creditor, rows in seen.items():
        future = [p for p in rows if p["due_date"] >= today]
        all_paid = all(p["balance_after"] == 0.0 for p in rows)

        if all_paid or not future:
            summaries.append({
                "creditor": creditor,
                "next_due_date": None,
                "next_amount": None,
                "balance": 0.0,
                "payments_left": 0,
                "paid_off": True,
                "due_soon": False,
            })
        else:
            nxt = future[0]
            summaries.append({
                "creditor": creditor,
                "next_due_date": nxt["due_date"],
                "next_amount": nxt["amount"],
                "balance": nxt["balance_before"],
                "payments_left": len(future),
                "paid_off": False,
                "due_soon": nxt["due_date"] <= cutoff,
            })

    return summaries


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    payments = load_payments(app.config["XLSX_FILE"])
    summaries = build_creditor_summaries(payments)
    monthly = get_monthly_summary(payments)
    return render_template("index.html", summaries=summaries, monthly=monthly)


@app.route("/add-settlement", methods=["POST"])
def add_settlement():
    creditor_name = request.form.get("creditor_name", "").strip()
    total_amount_str = request.form.get("total_amount", "").strip()
    monthly_payment_str = request.form.get("monthly_payment", "").strip()
    first_due_date_str = request.form.get("first_due_date", "").strip()
    payment_day_str = request.form.get("payment_day_of_month", "").strip()

    # Validate required fields
    if not creditor_name:
        return "Missing creditor_name", 400

    try:
        total_amount = float(total_amount_str)
        monthly_payment = float(monthly_payment_str)
    except ValueError:
        return "Invalid amount", 400

    try:
        first_due_date = datetime.strptime(first_due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format, expected YYYY-MM-DD", 400

    payment_day = int(payment_day_str) if payment_day_str.isdigit() else None

    rows = generate_payment_rows(
        creditor_name, total_amount, monthly_payment,
        first_due_date, payment_day_of_month=payment_day,
    )
    append_to_excel(rows, app.config["XLSX_FILE"])

    flash(f"Added {len(rows)} payments for {creditor_name}.", "success")
    return redirect(url_for("index"))


@app.route("/delete-settlement", methods=["POST"])
def delete_settlement():
    creditor_name = request.form.get("creditor_name", "").strip()
    if not creditor_name:
        return "Missing creditor_name", 400

    try:
        remove_creditor(creditor_name, app.config["XLSX_FILE"])
        flash(f"Removed all payments for {creditor_name}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")

    return redirect(url_for("index"))


@app.route("/sync")
def sync():
    try:
        payments = load_payments(app.config["XLSX_FILE"])
        upcoming = get_upcoming_payments(payments, days=14)
        event_ids = create_calendar_events(upcoming, all_payments=payments)
        message = f"{len(event_ids)} calendar event(s) created successfully."
        status = "success"
    except Exception as exc:
        message = f"Error syncing to Google Calendar: {exc}"
        status = "error"

    return render_template("sync.html", message=message, status=status)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
