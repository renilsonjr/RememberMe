"""Google Calendar adapter implementation."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.domain.payment import Payment

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Reminder times: 14 days and 7 days in minutes
_REMINDER_MINUTES = [14 * 24 * 60, 7 * 24 * 60]


class GoogleCalendarAdapter:
    """Adapter for Google Calendar API."""

    def __init__(self, credentials_file: str = "credentials.json"):
        """Initialize with path to credentials file."""
        self.credentials_file = credentials_file
        self.token_file = "token.json"
        self.service = self._build_service()

    def _build_service(self):
        """Authenticate and return a Google Calendar API service object."""
        creds = None

        # Try to load saved token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(self.token_file, "w") as fh:
                fh.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def create_event(self, payment: Payment, payments_remaining: int) -> str:
        """Create a calendar event for a payment."""
        body = self._build_event(payment, payments_remaining)
        result = self.service.events().insert(calendarId="primary", body=body).execute()
        return result.get("id")

    def create_events(self, payments: list[Payment]) -> list[str]:
        """
        Create multiple calendar events.

        Payments must be from the same repository to accurately count
        remaining payments per creditor.
        """
        if not payments:
            return []

        event_ids = []
        # Count total payments per creditor for accurate "remaining" count
        creditor_counts: dict[str, int] = {}
        for p in payments:
            creditor_counts[p.creditor] = creditor_counts.get(p.creditor, 0) + 1

        # Create events
        for payment in payments:
            total_for_creditor = creditor_counts[payment.creditor]
            remaining = total_for_creditor - payment.payment_num
            event_id = self.create_event(payment, remaining)
            event_ids.append(event_id)

        return event_ids

    @staticmethod
    def _build_event(payment: Payment, payments_remaining: int) -> dict:
        """Build a Google Calendar event dict from a payment."""
        creditor = payment.creditor
        amount = payment.amount
        num = payment.payment_num
        balance_after = payment.balance_after
        due_date = payment.due_date

        # Build title
        if payment.is_final():
            title = f"✅ {creditor} — FINAL PAYMENT ${amount:.2f}"
        else:
            title = f"{creditor} — ${amount:.2f} due"

        # Build description
        payments_word = "payment" if payments_remaining == 1 else "payments"
        description = (
            f"Payment #{num} | Balance after: ${balance_after:.2f} | "
            f"{payments_remaining} {payments_word} left"
        )

        return {
            "summary": title,
            "description": description,
            "start": {"date": due_date.isoformat()},
            "end": {"date": due_date.isoformat()},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": m} for m in _REMINDER_MINUTES
                ],
            },
        }
