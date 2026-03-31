"""
Smoke test — creates ONE real event on today's date to verify the Google
Calendar API connection and OAuth credentials work end-to-end.

Usage:
    python3 smoke_test_calendar.py

Prerequisites:
    1. Place your OAuth credentials file at credentials.json (or pass --creds <path>)
    2. On first run a browser window will open for OAuth consent; token.json is
       saved for subsequent runs.

The created event is titled "🧪 TEST EVENT - DELETE ME" so it is easy to find
and remove from your calendar.
"""

import argparse
from datetime import date

from calendar_events import _build_service

CALENDAR_ID = "primary"


def main(credentials_file: str = "credentials.json") -> None:
    today = date.today().isoformat()

    event_body = {
        "summary": "🧪 TEST EVENT - DELETE ME",
        "description": (
            "This event was created by smoke_test_calendar.py to verify "
            "that the Google Calendar API connection works correctly.\n"
            "It is safe to delete."
        ),
        "start": {"date": today},
        "end": {"date": today},
        "reminders": {"useDefault": False, "overrides": []},
    }

    print(f"Authenticating with credentials: {credentials_file}")
    service = _build_service(credentials_file)

    print(f"Creating test event on {today}...")
    result = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()

    event_id = result.get("id")
    event_link = result.get("htmlLink")
    print(f"\n✅ Event created successfully!")
    print(f"   ID:   {event_id}")
    print(f"   Link: {event_link}")
    print(f"\nOpen the link above to confirm, then delete the event.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test for Google Calendar API")
    parser.add_argument(
        "--creds",
        default="credentials.json",
        help="Path to OAuth credentials JSON file (default: credentials.json)",
    )
    args = parser.parse_args()
    main(credentials_file=args.creds)
