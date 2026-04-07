# Clean Architecture Solution for Settlement Tracker

## Current State Analysis

### Issues with Current Architecture

1. **Mixed Concerns**: `app.py` contains both Flask routing and business logic
2. **No Clear Dependency Boundaries**: Business logic scattered across modules
3. **Tight Coupling**: Direct imports between modules without abstraction
4. **No Repository Pattern**: Data access logic mixed with business logic in `reader.py` and `excel_writer.py`
5. **No Entity/Domain Models**: Using raw dicts for payments (no type safety)
6. **No Use Cases/Services**: No clear orchestration layer
7. **Tests Depend on File I/O**: Tests read actual Excel files instead of mocking infrastructure
8. **Configuration Scattered**: File paths and constants in multiple places

---

## Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│  UI/Framework Layer (Flask routes)      │ ← Controllers
├─────────────────────────────────────────┤
│  Use Cases/Application Services         │ ← Business rules
├─────────────────────────────────────────┤
│  Entities/Domain Models                 │ ← Core business logic
├─────────────────────────────────────────┤
│  Interface Adapters (Repositories)      │ ← Data abstraction
├─────────────────────────────────────────┤
│  Frameworks & Drivers                   │ ← External integrations
└─────────────────────────────────────────┘
```

---

## Proposed Project Structure

```
settlement-tracker/
├── src/
│   ├── domain/                          # Core business entities
│   │   ├── __init__.py
│   │   ├── payment.py                   # Payment entity
│   │   ├── settlement.py                # Settlement entity
│   │   └── errors.py                    # Domain-specific exceptions
│   │
│   ├── application/                     # Use cases & application services
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── payment_service.py       # Orchestrate payment operations
│   │   │   ├── calendar_service.py      # Orchestrate calendar operations
│   │   │   └── settlement_service.py    # Orchestrate settlement operations
│   │   │
│   │   └── dto/                         # Data transfer objects
│   │       ├── __init__.py
│   │       └── payment_dto.py           # DTOs for requests/responses
│   │
│   ├── infrastructure/                  # External integrations & repositories
│   │   ├── __init__.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base_repository.py       # Abstract repository
│   │   │   └── excel_repository.py      # Excel implementation
│   │   │
│   │   ├── calendar/
│   │   │   ├── __init__.py
│   │   │   ├── google_calendar_api.py   # Google Calendar adapter
│   │   │   └── calendar_gateway.py      # Abstract calendar interface
│   │   │
│   │   └── config.py                    # Configuration management
│   │
│   ├── presentation/                    # Flask layer (controllers/routes)
│   │   ├── __init__.py
│   │   ├── app.py                       # Flask app factory
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard_routes.py      # Dashboard endpoints
│   │   │   └── settlement_routes.py     # Settlement CRUD endpoints
│   │   │
│   │   └── templates/
│   │       └── index.html
│   │
│   └── __init__.py
│
├── tests/                               # Test suite
│   ├── __init__.py
│   ├── unit/
│   │   ├── domain/
│   │   │   └── test_payment.py
│   │   └── application/
│   │       └── test_payment_service.py
│   │
│   ├── integration/
│   │   ├── infrastructure/
│   │   │   └── test_excel_repository.py
│   │   └── presentation/
│   │       └── test_dashboard_routes.py
│   │
│   └── conftest.py                      # Shared test fixtures
│
├── requirements.txt
├── README.md
├── CLEAN_ARCHITECTURE_SOLUTION.md
└── RememberMe.xlsx
```

---

## Key Implementation Details

### 1. Domain Layer (Business Logic)

**`src/domain/payment.py`**
```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class Payment:
    """Immutable payment entity."""
    creditor: str
    payment_num: int
    amount: Decimal
    due_date: date
    balance_before: Decimal
    balance_after: Decimal
    
    def is_final(self) -> bool:
        return self.balance_after == 0
    
    def is_due_soon(self, days: int) -> bool:
        from datetime import timedelta
        return self.due_date <= date.today() + timedelta(days=days)

@dataclass(frozen=True)
class Settlement:
    """A creditor's complete payment schedule."""
    creditor: str
    payments: list[Payment]
    
    @property
    def is_paid_off(self) -> bool:
        return all(p.is_final() for p in self.payments)
    
    @property
    def next_payment(self) -> Payment | None:
        today = date.today()
        future = [p for p in self.payments if p.due_date >= today]
        return future[0] if future else None
```

**`src/domain/errors.py`**
```python
class SettlementError(Exception):
    """Base exception for domain errors."""
    pass

class SettlementNotFoundError(SettlementError):
    """Settlement doesn't exist."""
    pass

class InvalidPaymentError(SettlementError):
    """Payment data is invalid."""
    pass
```

---

### 2. Application Layer (Use Cases)

**`src/application/services/payment_service.py`**
```python
from decimal import Decimal
from datetime import date
from typing import Protocol

class PaymentRepository(Protocol):
    """Abstract repository interface."""
    def get_all(self) -> list[Payment]: ...
    def add_settlement(self, settlement: Settlement) -> None: ...
    def remove_settlement(self, creditor: str) -> None: ...

class PaymentService:
    """Use cases for payment management."""
    
    def __init__(self, repository: PaymentRepository):
        self.repository = repository
    
    def get_upcoming_payments(self, days: int = 14) -> list[Payment]:
        """Get all payments due within N days."""
        all_payments = self.repository.get_all()
        return [p for p in all_payments if p.is_due_soon(days)]
    
    def create_settlement(self, creditor: str, total: Decimal, 
                         monthly: Decimal, first_due: date) -> Settlement:
        """Create a new payment schedule."""
        payments = self._generate_schedule(
            creditor, total, monthly, first_due
        )
        settlement = Settlement(creditor, payments)
        self.repository.add_settlement(settlement)
        return settlement
    
    def remove_settlement(self, creditor: str) -> None:
        """Delete a creditor's schedule."""
        self.repository.remove_settlement(creditor)
    
    @staticmethod
    def _generate_schedule(...) -> list[Payment]:
        # Payment schedule generation logic
        pass
```

---

### 3. Infrastructure Layer (Adapters)

**`src/infrastructure/repositories/excel_repository.py`**
```python
from src.domain.payment import Payment, Settlement
from src.domain.errors import SettlementNotFoundError
import openpyxl

class ExcelRepository:
    """Payment data repository backed by Excel file."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def get_all(self) -> list[Payment]:
        """Load all payments from Excel."""
        wb = openpyxl.load_workbook(self.filepath, data_only=True)
        ws = wb.active
        payments = []
        
        for row in ws.iter_rows(min_row=4, values_only=True):
            payment = self._row_to_payment(row)
            if payment:
                payments.append(payment)
        
        return payments
    
    def add_settlement(self, settlement: Settlement) -> None:
        """Append a settlement to Excel."""
        # Implementation
        pass
    
    def remove_settlement(self, creditor: str) -> None:
        """Remove a creditor from Excel."""
        # Implementation
        pass
    
    @staticmethod
    def _row_to_payment(row) -> Payment | None:
        """Convert Excel row to Payment entity."""
        # Convert and validate
        pass
```

**`src/infrastructure/calendar/calendar_gateway.py`**
```python
from typing import Protocol
from src.domain.payment import Payment

class CalendarGateway(Protocol):
    """Abstract interface for calendar operations."""
    def create_event(self, payment: Payment, reminders: list[int]) -> str:
        """Create a calendar event for a payment."""
        ...
    
    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event."""
        ...

class GoogleCalendarAdapter:
    """Adapter for Google Calendar API."""
    
    def __init__(self, credentials_path: str = "credentials.json"):
        self.service = self._build_service(credentials_path)
    
    def create_event(self, payment: Payment, reminders: list[int]) -> str:
        """Create event in Google Calendar."""
        # Implementation using self.service
        pass
```

---

### 4. Presentation Layer (Flask)

**`src/presentation/app.py`**
```python
from flask import Flask
from src.infrastructure.repositories.excel_repository import ExcelRepository
from src.infrastructure.calendar.google_calendar_adapter import GoogleCalendarAdapter
from src.application.services.payment_service import PaymentService
from src.presentation.routes.dashboard_routes import create_dashboard_bp

def create_app(config=None):
    """Flask app factory."""
    app = Flask(__name__)
    
    # Setup
    if config:
        app.config.update(config)
    
    # Infrastructure
    repository = ExcelRepository(app.config.get("XLSX_FILE"))
    calendar_gateway = GoogleCalendarAdapter()
    
    # Services
    payment_service = PaymentService(repository)
    
    # Register routes
    dashboard_bp = create_dashboard_bp(payment_service, calendar_gateway)
    app.register_blueprint(dashboard_bp)
    
    return app

if __name__ == "__main__":
    app = create_app({"XLSX_FILE": "RememberMe.xlsx"})
    app.run(debug=True, port=5000)
```

**`src/presentation/routes/dashboard_routes.py`**
```python
from flask import Blueprint, render_template, request
from src.application.services.payment_service import PaymentService

def create_dashboard_bp(payment_service: PaymentService, calendar_gateway):
    bp = Blueprint("dashboard", __name__)
    
    @bp.route("/")
    def index():
        """Render dashboard."""
        upcoming = payment_service.get_upcoming_payments(days=14)
        # Aggregate for display...
        return render_template("index.html", creditors=creditor_list)
    
    @bp.route("/api/settlements", methods=["POST"])
    def create_settlement():
        """Create new settlement."""
        data = request.json
        try:
            settlement = payment_service.create_settlement(
                creditor=data["creditor"],
                total=Decimal(data["total"]),
                monthly=Decimal(data["monthly"]),
                first_due=date.fromisoformat(data["first_due"])
            )
            return {"status": "ok", "creditor": settlement.creditor}, 201
        except Exception as e:
            return {"error": str(e)}, 400
    
    return bp
```

---

## Benefits of This Architecture

| Aspect | Benefit |
|--------|---------|
| **Testability** | Services, entities, and repositories can be unit tested in isolation |
| **Maintainability** | Clear separation of concerns makes changes localized |
| **Flexibility** | Swap repositories (Excel → SQL) or calendar (Google → Outlook) without affecting services |
| **Scalability** | Can add new features (API endpoints, CLI, mobile app) by creating new presentation layers |
| **Reusability** | Services and domain logic reusable across multiple UIs (web, CLI, etc.) |
| **Type Safety** | Entities and DTOs provide structure vs. raw dicts |
| **Configuration** | Centralized in `infrastructure/config.py` |
| **Error Handling** | Domain-specific exceptions for better error management |

---

## Migration Path

### Phase 1: Setup Infrastructure
1. Create directory structure
2. Define domain entities (`payment.py`, `settlement.py`, `errors.py`)
3. Extract repository interfaces

### Phase 2: Implement Services
4. Implement `PaymentService` using existing logic from `reader.py`
5. Implement `CalendarService` wrapping `calendar_events.py`
6. Create DTOs for data transfer

### Phase 3: Refactor Presentation
7. Create Flask app factory in `presentation/app.py`
8. Convert routes to blueprints in `presentation/routes/`
9. Inject services into routes

### Phase 4: Infrastructure Adapters
10. Implement `ExcelRepository` wrapping `excel_writer.py`
11. Implement `GoogleCalendarAdapter` wrapping `calendar_events.py`
12. Update tests to use mocks

### Phase 5: Cleanup
13. Delete old top-level `app.py`, `main.py`, `reader.py`, etc.
14. Update `requirements.txt` if needed
15. Move tests to `tests/` directory with new structure

---

## Key Principles to Follow

1. **Dependency Rule**: Only depend inward (presentation → application → domain)
2. **Interface Segregation**: Services accept protocol types, not concrete classes
3. **Immutability**: Domain entities are frozen dataclasses
4. **Repository Pattern**: All data access goes through repositories
5. **No Framework Leakage**: Business logic has no Flask, openpyxl, or Google dependencies
6. **Tested at Boundaries**: Test presentation via HTTP, infrastructure via contracts

---

## Next Steps

1. Would you like me to implement Phase 1 (domain layer) first?
2. Do you want to migrate gradually (keep old code) or refactor fully?
3. Should we add any new layers (e.g., validation/business rules)?
