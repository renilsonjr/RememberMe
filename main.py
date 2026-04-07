#!/usr/bin/env python3
"""
Terminal calendar sync for RememberMe debt tracker.

Run with: python3 main.py

Displays upcoming payments and syncs them to Google Calendar.
"""

import os
from src.infrastructure.repositories.excel_repository import ExcelRepository
from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter
from src.application.services.payment_service import PaymentService
from src.application.services.calendar_service import CalendarService


def main():
    """Run the terminal interface."""
    xlsx_file = os.path.join(os.path.dirname(__file__), "RememberMe.xlsx")

    # Initialize infrastructure
    repository = ExcelRepository(xlsx_file)
    calendar_gateway = GoogleCalendarAdapter()

    # Initialize services
    payment_service = PaymentService(repository)
    calendar_service = CalendarService(repository, calendar_gateway)

    # Get upcoming payments
    upcoming = payment_service.get_upcoming_payments(days=14)

    if not upcoming:
        print("No payments due in the next 14 days.")
        return

    print(f"Upcoming payments ({len(upcoming)} found):")
    print("-" * 52)

    for p in upcoming:
        final_tag = "  ← FINAL PAYMENT" if p.is_final else ""
        print(
            f"  {p.creditor:<12} | ${p.amount:>7.2f} due {p.due_date} "
            f"| Balance after: ${p.balance_after:>9.2f}{final_tag}"
        )

    print("-" * 52)
    print("Creating Google Calendar events...")
    event_ids = calendar_service.sync_upcoming_payments(days=14)
    print(f"✅ {len(event_ids)} event(s) created.")


if __name__ == "__main__":
    main()
