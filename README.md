# Settlement Tracker

Reads a debt-settlement payment schedule from an Excel spreadsheet and creates Google Calendar events for any payments due in the next 14 days, with pop-up reminders at 7 and 14 days in advance.

## How it works

1. **`reader.py`** — loads `settlement_tracker.xlsx`, parses the payment schedule (creditor, amount, due date, running balance), and filters for upcoming payments within a configurable window.
2. **`calendar_events.py`** — authenticates with the Google Calendar API via OAuth 2.0 and creates a calendar event for each upcoming payment. Final payments are flagged with a ✅ in the event title.
3. **`main.py`** — ties it together: load → filter → print summary → create events.

## Spreadsheet format

The workbook must have **3 header rows** followed by data rows with these columns (in order):

| Column | Description |
|---|---|
| A | Creditor name |
| B | Payment number |
| C | Payment amount |
| D | Due date |
| E | Balance before payment |
| F | Balance after payment (formula cells are handled automatically) |

Blank rows between creditor groups are ignored.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Calendar credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Google Calendar API**.
3. Create **OAuth 2.0 credentials** (Desktop app) and download the file as `credentials.json` in the project root.

On first run, a browser window will open for you to authorize access. The token is saved to `token.json` and reused on subsequent runs.

### 3. Add your spreadsheet

Copy your `settlement_tracker.xlsx` file into the project root. It is gitignored and never committed.

## Usage

```bash
python3 main.py
```

Example output:

```
Upcoming payments (2 found):
----------------------------------------------------
  Bank A  |  $200.00 due 2026-04-05  |  Balance after: $800.00
  Credit Union B  |  $150.00 due 2026-04-08  |  Balance after: $0.00  ← FINAL PAYMENT
----------------------------------------------------
Creating Google Calendar events...
✅ 2 event(s) created.
```

## Running tests

```bash
pytest
```

Tests cover the Excel reader, upcoming-payment filtering, paid-off detection, and calendar event building — all without requiring real files or a live Google API connection.

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point |
| `reader.py` | Excel parsing and payment filtering |
| `calendar_events.py` | Google Calendar API integration |
| `test_reader.py` | Unit tests for the reader |
| `test_calendar.py` | Unit tests for calendar event building |
| `test_main.py` | Integration tests for the main flow |
| `smoke_test_calendar.py` | Manual smoke test against the live Calendar API |
| `settlement_tracker.xlsx` | Your data file — **gitignored, add locally** |
| `credentials.json` | Google OAuth credentials — **gitignored** |
| `token.json` | Saved OAuth token — **gitignored** |
