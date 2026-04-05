# Run with: python3 main.py

import os
from reader import load_payments, get_upcoming_payments
from calendar_events import create_calendar_events

XLSX_FILE = os.path.join(os.path.dirname(__file__), "RememberMe.xlsx")


def run():
    payments = load_payments(XLSX_FILE)
    upcoming = get_upcoming_payments(payments, days=14)

    if not upcoming:
        print("No payments due in the next 14 days.")
        return

    print(f"Upcoming payments ({len(upcoming)} found):")
    print("-" * 52)

    for p in upcoming:
        is_final = p["balance_after"] == 0.0
        final_tag = "  ← FINAL PAYMENT" if is_final else ""
        print(
            f"  {p['creditor']}"
            f"  |  ${p['amount']:.2f} due {p['due_date']}"
            f"  |  Balance after: ${p['balance_after']:.2f}"
            f"{final_tag}"
        )

    print("-" * 52)
    print("Creating Google Calendar events...")
    event_ids = create_calendar_events(upcoming, all_payments=payments)
    print(f"✅ {len(event_ids)} event(s) created.")


if __name__ == "__main__":
    run()
