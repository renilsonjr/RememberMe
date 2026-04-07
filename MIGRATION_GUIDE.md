# Clean Architecture Migration Guide

This guide explains the new clean architecture implementation and how to use it.

## What Changed

The project has been refactored from a flat structure to a 5-layer clean architecture:

### Old Structure (Top-Level Files)
```
├── app.py           ← Flask + business logic mixed
├── main.py          ← Terminal entry point
├── reader.py        ← Data reading
├── excel_writer.py  ← Data writing
├── calendar_events.py ← Calendar logic
└── templates/       ← HTML templates
```

### New Structure (Organized by Layer)
```
src/
├── domain/              ← Core business entities
│   ├── payment.py       ← Payment & Settlement entities
│   └── errors.py        ← Domain exceptions
├── application/         ← Use cases & services
│   ├── services/        ← Business orchestration
│   │   ├── payment_service.py
│   │   ├── calendar_service.py
│   │   └── settlement_service.py
│   └── dto/             ← Data transfer objects
├── infrastructure/      ← External integrations
│   ├── repositories/    ← Data access abstraction
│   │   └── excel_repository.py
│   └── calendar/        ← Calendar integration
│       └── google_calendar_adapter.py
└── presentation/        ← Flask web layer
    ├── app.py           ← App factory
    ├── routes/          ← Route blueprints
    └── templates/       ← HTML templates

tests/                  ← Test suite (unit + integration)
```

## Key Improvements

### 1. **Type Safety**
**Before:** Using raw dicts
```python
payment = {"creditor": "X", "amount": 100.0, "due_date": date.today()}
```

**After:** Typed domain entities
```python
payment = Payment(creditor="X", amount=Decimal("100.00"), due_date=date.today())
```

### 2. **Clear Separation of Concerns**
- **Domain**: Pure business logic (Payment, Settlement entities)
- **Application**: Use cases (PaymentService, CalendarService)
- **Infrastructure**: External integrations (ExcelRepository, GoogleCalendarAdapter)
- **Presentation**: Web layer (Flask routes)

### 3. **Testability**
- Domain entities are testable without dependencies
- Services can be tested with mock repositories
- Flask routes tested via test client

```python
# Before: Tests depended on actual Excel files
def test_payment_loading():
    payments = load_payments("RememberMe.xlsx")  # Real file required

# After: Tests use fixtures with mocks
def test_payment_service(mock_repository):
    service = PaymentService(mock_repository)
    service.create_settlement(...)  # No real file needed
```

### 4. **Loose Coupling**
Services depend on abstract interfaces (Protocols), not concrete implementations:

```python
class PaymentService:
    def __init__(self, repository: PaymentRepository):  # Interface, not ExcelRepository
        self.repository = repository
```

This means you can swap ExcelRepository for SqlRepository without changing the service.

### 5. **Configuration Management**
No more scattered configuration:

```python
# Before: File paths in multiple places
app.config["XLSX_FILE"] = os.path.join(os.path.dirname(__file__), "RememberMe.xlsx")

# After: Centralized in app factory
app = create_app({"XLSX_FILE": "RememberMe.xlsx"})
```

## Running the App

### Web Dashboard
```bash
# Same command as before
python3 app.py

# Now opens http://localhost:5000
```

### Terminal CLI
```bash
# Same command as before
python3 main.py

# Displays upcoming payments and syncs to Google Calendar
```

## Running Tests

### All Tests
```bash
pytest                    # Run all tests
pytest -v               # Verbose output
pytest --cov           # With coverage report
```

### Specific Test Categories
```bash
pytest tests/unit/       # Unit tests only (domain + services)
pytest tests/integration/ # Integration tests (with infrastructure)
```

### Example Tests

**Domain Tests** (no dependencies)
```python
def test_payment_is_final():
    payment = Payment(
        creditor="X", payment_num=1, amount=Decimal("100"),
        due_date=date.today(), balance_before=Decimal("100"),
        balance_after=Decimal("0")  # Final payment
    )
    assert payment.is_final() == True
```

**Service Tests** (with mock repository)
```python
def test_create_settlement():
    repo = MockRepository()
    service = PaymentService(repo)
    settlement = service.create_settlement(
        creditor="X", total_amount=Decimal("500"),
        monthly_payment=Decimal("100"), first_due_date=date.today()
    )
    assert settlement.creditor == "X"
    assert len(settlement.payments) == 5
```

**Integration Tests** (with real Flask)
```python
def test_dashboard_index(client):
    response = client.get("/")
    assert response.status_code == 200
```

## API Reference

### Domain Entities

```python
from src.domain.payment import Payment, Settlement

# Create a payment
payment = Payment(
    creditor="SPOTLOAN",
    payment_num=1,
    amount=Decimal("50.00"),
    due_date=date(2026, 5, 1),
    balance_before=Decimal("500.00"),
    balance_after=Decimal("450.00")
)

# Check properties
payment.is_final()           # False
payment.is_due_soon(14)      # True if due within 14 days
payment.days_until_due()     # Days until due date

# Create a settlement
settlement = Settlement("SPOTLOAN", [payment1, payment2, ...])
settlement.is_paid_off       # True if final balance is 0
settlement.next_payment      # Next payment due
settlement.payments_remaining # Count of unpaid payments
```

### Services

```python
from src.application.services.payment_service import PaymentService

service = PaymentService(repository)

# Get payments
all_payments = service.get_all_payments()       # List of PaymentDTO
upcoming = service.get_upcoming_payments(14)    # Due within 14 days
summaries = service.get_all_summaries()         # SettlementSummaryDTO per creditor
monthly = service.get_monthly_summary()         # MonthlySummaryDTO

# Create settlement
settlement = service.create_settlement(request)  # CreateSettlementRequestDTO
```

### Repository

```python
from src.infrastructure.repositories.excel_repository import ExcelRepository

repo = ExcelRepository("RememberMe.xlsx")

# Read
payments = repo.get_all_payments()      # List[Payment]
settlements = repo.get_all_settlements() # List[Settlement]
settlement = repo.get_settlement("SPOTLOAN")

# Write
repo.add_settlement(settlement)
repo.remove_settlement("SPOTLOAN")
repo.update_settlement(settlement)
```

### Calendar

```python
from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter

calendar = GoogleCalendarAdapter("credentials.json")

# Create events
event_id = calendar.create_event(payment, payments_remaining=5)
event_ids = calendar.create_events([payment1, payment2, ...])
```

## Backward Compatibility

The old `app.py`, `main.py`, `reader.py`, etc. at the root level **have been refactored** to use the new architecture. They now import from `src/` instead of containing logic directly.

```python
# Old app.py had ~150 lines with Flask + business logic
# New app.py:
from src.presentation.app import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(port=5000)
```

## Migration Checklist

If you had custom code depending on the old structure:

- ✅ Change imports from `from reader import load_payments` to `from src.infrastructure.repositories.excel_repository import ExcelRepository`
- ✅ Change imports from `from calendar_events import create_calendar_events` to `from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter`
- ✅ Create services instead of calling functions directly
- ✅ Use domain entities instead of dicts

### Example Migration

**Before:**
```python
payments = load_payments("RememberMe.xlsx")
upcoming = get_upcoming_payments(payments, days=14)
create_calendar_events(upcoming, all_payments=payments)
```

**After:**
```python
from src.infrastructure.repositories.excel_repository import ExcelRepository
from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter
from src.application.services.payment_service import PaymentService
from src.application.services.calendar_service import CalendarService

repo = ExcelRepository("RememberMe.xlsx")
calendar = GoogleCalendarAdapter("credentials.json")

payment_service = PaymentService(repo)
calendar_service = CalendarService(repo, calendar)

upcoming = payment_service.get_upcoming_payments(days=14)
event_ids = calendar_service.sync_upcoming_payments(days=14)
```

## Next Steps

1. **Run tests** to verify everything works:
   ```bash
   pytest -v
   ```

2. **Update any custom integrations** to use the new service APIs

3. **Consider adding new features** that benefit from the clean architecture:
   - REST API endpoints (new presentation layer)
   - CLI application (new presentation layer)
   - SQL database (new repository implementation)
   - Different calendar service (swap adapter)

## Questions?

- Check `CLEAN_ARCHITECTURE_SOLUTION.md` for the original design document
- Review test files in `tests/` for usage examples
- Look at service docstrings for API documentation

---

**Status:** ✅ All tests passing (23 tests)  
**Last Updated:** 2026-04-06
