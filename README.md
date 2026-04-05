# RememberMe

Never miss a debt payment again.

RememberMe reads your settlement spreadsheet and automatically creates Google Calendar events with reminders — so every upcoming payment shows up on your calendar 14 and 7 days before it's due.

---

## What it does

1. Reads all your payments from `RememberMe.xlsx`
2. Finds payments due within the next 14 days
3. Creates a Google Calendar event for each one with:
   - The creditor name, amount, and due date in the title
   - Balance remaining and payments left in the description
   - Popup reminders 14 days and 7 days before the due date
   - A special ✅ title for your final payment on each debt

---

## Project structure

```
RememberMe/
├── RememberMe.xlsx          ← your payment spreadsheet (not committed)
├── reader.py                ← reads and filters payments from xlsx
├── calendar_events.py       ← creates Google Calendar events
├── main.py                  ← entry point, ties everything together
├── test_reader.py           ← tests for reader.py
├── test_calendar.py         ← tests for calendar_events.py (mocked API)
├── test_main.py             ← integration tests for main.py
├── smoke_test_calendar.py   ← manual API connection test
└── requirements.txt
```

---

## Setup

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Set up your data

**Step 1 — Download the template**

Download `RememberMe_template.xlsx` from the repo and rename it to `RememberMe.xlsx`.

**Step 2 — Fill in the BLUE columns only**

| Column | Name | What to enter |
|--------|------|---------------|
| A | Creditor Name | The name of the lender or creditor (e.g. "SPOTLOAN") |
| B | Payment # | The payment number in sequence: 1, 2, 3… |
| C | Payment Amount | The dollar amount of this payment |
| D | Due Date | The date this payment is due |
| E | Balance Before | The balance owed before this payment is made |

**Step 3 — Leave the grey column alone**

| Column | Name | Notes |
|--------|------|-------|
| F | Balance After | Auto-calculated — do not edit |

RememberMe reads this column as a formula. If the cell is empty it computes `Balance Before − Payment Amount` automatically.

**Step 4 — Follow these rules**

- One row per payment — enter the **entire schedule upfront**, not just the next payment
- Leave a **blank row between each creditor** to visually separate them (blank rows are ignored when reading)
- Place the completed file in the **project root folder**, the same level as `main.py`

```
settlement-tracker/
├── RememberMe.xlsx   ← here
├── main.py
├── reader.py
└── ...
```

---

### 4. Connect Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**
2. Enable the **Google Calendar API** for your project
3. Create an **OAuth 2.0 Client ID** (Desktop app type)
4. Download the JSON file and save it as `credentials.json` in the project folder

On first run, a browser window will open for you to authorize access. A `token.json` file is saved automatically for future runs — no repeated sign-ins.

---

## Usage

```bash
python3 main.py
```

Example output:

```
Upcoming payments (2 found):
----------------------------------------------------
  MCM        |  $44.35 due 2026-04-07  |  Balance after: $886.90
  SPOTLOAN   |  $24.17 due 2026-04-10  |  Balance after: $199.40
----------------------------------------------------
Creating Google Calendar events...
✅ 2 event(s) created.
```

### Verify the API connection

Before running for real, you can create a single test event to confirm your credentials work:

```bash
python3 smoke_test_calendar.py
```

This creates one event titled **"🧪 TEST EVENT - DELETE ME"** on today's date. Check your calendar and delete it once confirmed.

---

## Running tests

```bash
pytest test_reader.py test_calendar.py test_main.py -v
```

All Google Calendar API calls are mocked — no credentials needed to run tests.

```
58 passed in 0.29s
```

---

## Security notes

The following files are excluded from version control via `.gitignore`:

- `credentials.json` — your Google OAuth client secret
- `token.json` — your saved access token
- `RememberMe.xlsx` — your personal payment data
- `.env` — any local environment overrides

Never commit these files.

---

## Requirements

- Python 3.10+
- `openpyxl` — reads the xlsx spreadsheet
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client` — Google Calendar integration
- `pytest` — test runner
