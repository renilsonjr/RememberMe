from __future__ import annotations

import os
from collections import defaultdict
from datetime import date

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

_REMINDER_MINUTES = [14 * 24 * 60, 7 * 24 * 60]  # 14 days, 7 days in minutes


def _build_service(credentials_file: str = "credentials.json"):
    """Authenticate and return a Google Calendar API service object."""
    creds = None
    token_file = "token.json"

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as fh:
            fh.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _payments_left(payments: list[dict], creditor: str, current_index_in_group: int) -> int:
    """Return the number of payments remaining after the current one for a creditor."""
    creditor_payments = [p for p in payments if p["creditor"] == creditor]
    return len(creditor_payments) - current_index_in_group - 1


def _build_event(payment: dict, payments_remaining: int) -> dict:
    creditor = payment["creditor"]
    amount = payment["amount"]
    num = payment["payment_num"]
    balance_after = payment["balance_after"]
    due_date: date = payment["due_date"]

    is_final = balance_after == 0.0

    if is_final:
        title = f"✅ {creditor} — FINAL PAYMENT ${amount:.2f}"
    else:
        title = f"{creditor} — ${amount:.2f} due"

    payments_left_str = (
        f"{payments_remaining} payment{'s' if payments_remaining != 1 else ''} left"
    )
    description = (
        f"Payment #{num} | Balance after: ${balance_after:.2f} | {payments_left_str}"
    )

    date_str = due_date.isoformat()

    return {
        "summary": title,
        "description": description,
        "start": {"date": date_str},
        "end": {"date": date_str},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": m} for m in _REMINDER_MINUTES
            ],
        },
    }


def create_calendar_events(
    payments: list[dict],
    credentials_file: str = "credentials.json",
) -> list[str]:
    """
    Create a Google Calendar event for each payment.

    Returns a list of created event IDs.
    """
    if not payments:
        return []

    service = _build_service(credentials_file)

    # Track per-creditor position to compute payments_left
    creditor_counters: dict[str, int] = defaultdict(int)

    event_ids = []
    for payment in payments:
        creditor = payment["creditor"]
        idx_in_group = creditor_counters[creditor]
        remaining = _payments_left(payments, creditor, idx_in_group)
        creditor_counters[creditor] += 1

        body = _build_event(payment, remaining)
        result = service.events().insert(calendarId="primary", body=body).execute()
        event_ids.append(result.get("id"))

    return event_ids
