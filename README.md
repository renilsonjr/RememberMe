# RememberMe

Never miss a debt payment again.

RememberMe reads your settlement spreadsheet and automatically creates Google Calendar events with reminders — so every upcoming payment shows up on your calendar 14 and 7 days before it's due. It also includes a web dashboard for managing all your creditors in one place.

---

## Features

- Reads payment schedules from `RememberMe.xlsx`
- Creates Google Calendar events with 14-day and 7-day popup reminders
- Web dashboard at `localhost:5000` showing all creditors at a glance
- Payments due within 14 days highlighted in yellow
- Add new settlements via web form — auto-generates the full payment schedule
- Remove settlements directly from the dashboard with a confirmation prompt
- Paid off creditors shown with a green badge

---

## Project structure

```
RememberMe/
├── app.py                    ← web dashboard
├── main.py                   ← terminal calendar sync
├── reader.py                 ← reads Excel data
├── calendar_events.py        ← Google Calendar integration
├── excel_writer.py           ← adds/removes settlements in Excel
├── templates/
│   └── index.html            ← dashboard UI
├── RememberMe_template.xlsx  ← template for new users
├── requirements.txt
├── test_app.py
├── test_calendar.py
├── test_excel_writer.py
├── test_main.py
└── test_reader.py
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
- Place the completed file in the **project root folder**, the same level as `app.py`

```
RememberMe/
├── RememberMe.xlsx   ← here
├── app.py
├── reader.py
└── ...
```

---

### 3. Connect Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**
2. Enable the **Google Calendar API** for your project
3. Create an **OAuth 2.0 Client ID** (Desktop app type)
4. Download the JSON file and save it as `credentials.json` in the project folder

On first run, a browser window will open for you to authorize access. A `token.json` file is saved automatically for future runs — no repeated sign-ins.

---

## Running the app

**Web dashboard** (recommended):

```bash
python3 app.py
```

Then open `http://localhost:5000` in your browser. From the dashboard you can view all creditors, add new settlements, remove existing ones, and sync to Google Calendar.

**Terminal calendar sync only:**

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

**Run the test suite:**

```bash
pytest
```

All Google Calendar API calls are mocked — no credentials needed to run tests.

```
124 passed in 0.54s
```

### Verify the API connection

Before running for real, you can create a single test event to confirm your credentials work:

```bash
python3 smoke_test_calendar.py
```

This creates one event titled **"🧪 TEST EVENT - DELETE ME"** on today's date. Check your calendar and delete it once confirmed.

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
- `flask` — web dashboard
- `openpyxl` — reads and writes the xlsx spreadsheet
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client` — Google Calendar integration
- `pytest` — test runner
