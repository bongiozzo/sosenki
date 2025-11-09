# SOSenki - Payment and Debt Management System

A comprehensive Telegram-based payment management system for shared properties with sophisticated billing features, balance tracking, and multi-period financial management.

## Features

### Core Features (MVP)
- **Service Period Management**: Create and manage financial periods (monthly, quarterly, etc.)
- **Contribution Tracking**: Record owner payments with full history and audit trail
- **Expense Recording**: Track community expenses with payer attribution
- **Balance Calculation**: Generate detailed balance sheets with owner-specific financials

### Advanced Features  
- **Flexible Allocation Strategies**:
  - Proportional allocation (divide costs by ownership percentage)
  - Fixed fee allocation (equal distribution)
  - Usage-based allocation (meter readings)
- **Utility Meter Readings**: Track consumption-based costs
- **Service Charges**: Apply per-owner charges (maintenance fees, penalties, etc.)
- **Budget Items**: Categorize and track budgeted expenses

### Multi-Period Management
- **Balance Carry-Forward**: Automatically transfer period balances to next period
  - Credits become opening contributions
  - Debts become opening service charges
- **Multi-Period Reconciliation**: Track financial chains across multiple periods
- **Period Transitions**: Smooth period closing and opening workflows

## Architecture

### Technology Stack
- **Backend**: Python 3.11+ with FastAPI
- **Database**: SQLite (development) / PostgreSQL (production) with SQLAlchemy ORM
- **Telegram Integration**: python-telegram-bot with async webhooks
- **Migrations**: Alembic for database schema management
- **Testing**: pytest with 260+ comprehensive tests

### Project Structure
```
src/
├── api/
│   ├── webhook.py           # FastAPI webhook for Telegram
│   ├── payment.py           # Payment management REST API
│   └── mini_app.py          # Telegram Mini App endpoints
├── bot/                      # Telegram bot handlers
├── models/
│   └── payment/             # Financial data models
│       ├── service_period.py
│       ├── contribution_ledger.py
│       ├── expense_ledger.py
│       ├── service_charge.py
│       ├── budget_item.py
│       └── utility_reading.py
├── services/
│   ├── payment_service.py         # Period & transaction management
│   ├── balance_service.py         # Balance calculations & reporting
│   └── allocation_service.py      # Expense allocation strategies
└── main.py                  # Application entry point

tests/
├── unit/                    # Unit tests (80+ tests)
├── integration/             # Integration tests (100+ tests)
└── contract/                # API contract tests (40+ tests)
```

## API Documentation

### Base URL
```
/api/payments
```

### Service Period Endpoints

#### Create Period
```
POST /periods
Content-Type: application/json

{
  "name": "November 2025",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "description": "Monthly operational period"
}

Response: 201 Created
{
  "id": 1,
  "name": "November 2025",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "status": "OPEN",
  "description": "Monthly operational period",
  "closed_at": null
}
```

#### Get Period
```
GET /periods/{period_id}

Response: 200 OK
{
  "id": 1,
  "name": "November 2025",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "status": "OPEN",
  "description": "Monthly operational period",
  "closed_at": null
}
```

#### List Periods
```
GET /periods

Response: 200 OK
{
  "periods": [
    {
      "id": 1,
      "name": "November 2025",
      "start_date": "2025-11-01",
      "end_date": "2025-11-30",
      "status": "OPEN"
    }
  ]
}
```

#### Close Period
```
POST /periods/{period_id}/close

Response: 200 OK
{
  "id": 1,
  "status": "CLOSED",
  "closed_at": "2025-12-01T10:30:00Z"
}
```

### Contribution Endpoints

#### Record Contribution
```
POST /periods/{period_id}/contributions
Content-Type: application/json

{
  "user_id": 1,
  "amount": "1000.00",
  "comment": "Monthly payment"
}

Response: 201 Created
{
  "id": 101,
  "service_period_id": 1,
  "user_id": 1,
  "amount": "1000.00",
  "date": "2025-11-15T10:30:00Z",
  "comment": "Monthly payment"
}
```

#### List Contributions
```
GET /periods/{period_id}/contributions?owner_id={owner_id}

Response: 200 OK
[
  {
    "id": 101,
    "service_period_id": 1,
    "user_id": 1,
    "amount": "1000.00",
    "date": "2025-11-15T10:30:00Z",
    "comment": "Monthly payment"
  }
]
```

### Expense Endpoints

#### Record Expense
```
POST /periods/{period_id}/expenses
Content-Type: application/json

{
  "paid_by_user_id": 1,
  "amount": "5000.00",
  "payment_type": "Maintenance",
  "vendor": "ABC Maintenance Co",
  "description": "Monthly building maintenance"
}

Response: 201 Created
```

#### List Expenses
```
GET /periods/{period_id}/expenses

Response: 200 OK
[
  {
    "id": 201,
    "service_period_id": 1,
    "paid_by_user_id": 1,
    "amount": "5000.00",
    "payment_type": "Maintenance",
    "date": "2025-11-15T10:30:00Z",
    "vendor": "ABC Maintenance Co",
    "description": "Monthly building maintenance"
  }
]
```

### Balance Sheet Endpoints

#### Generate Balance Sheet
```
GET /periods/{period_id}/balance-sheet

Response: 200 OK
{
  "period_id": 1,
  "entries": [
    {
      "owner_id": 1,
      "username": "alice",
      "total_contributions": "1000.00",
      "total_expenses": "500.00",
      "total_charges": "200.00",
      "balance": "300.00"
    },
    {
      "owner_id": 2,
      "username": "bob",
      "total_contributions": "800.00",
      "total_expenses": "0.00",
      "total_charges": "300.00",
      "balance": "500.00"
    }
  ],
  "total_period_balance": "800.00"
}
```

#### Get Owner Balance
```
GET /periods/{period_id}/owner-balance/{owner_id}

Response: 200 OK
{
  "owner_id": 1,
  "period_id": 1,
  "total_contributions": "1000.00",
  "total_expenses": "500.00",
  "total_charges": "200.00",
  "balance": "300.00"
}
```

### Multi-Period Endpoints

#### Carry Forward Balance
```
POST /periods/carry-forward
Content-Type: application/json

{
  "from_period_id": 1,
  "to_period_id": 2
}

Response: 200 OK
{
  "from_period_id": 1,
  "to_period_id": 2,
  "carried_forward_owners": {
    "1": "300.00",
    "2": "500.00"
  },
  "total_carried": "800.00",
  "message": "Successfully carried forward 2 owner balances"
}
```

#### Get Opening Transactions
```
GET /periods/{period_id}/opening-transactions

Response: 200 OK
{
  "period_id": 2,
  "opening_contributions": [
    {
      "id": 102,
      "user_id": 1,
      "amount": "300.00",
      "date": "2025-12-01T00:00:00Z",
      "comment": "Opening balance from previous period"
    }
  ],
  "opening_charges": [
    {
      "id": 201,
      "user_id": 3,
      "amount": "250.00",
      "description": "Opening debt from previous period"
    }
  ],
  "total_opening_contributions": "300.00",
  "total_opening_charges": "250.00"
}
```

## Error Handling

The API returns standard HTTP status codes with detailed error messages:

### Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input or validation error
- `404 Not Found`: Resource not found
- `409 Conflict`: Business logic conflict (e.g., closed period, invalid state transition)
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "Descriptive error message"
}
```

### Common Error Scenarios

#### Period Not Found
```
404 Not Found
{
  "detail": "Period not found"
}
```

#### Period Closed for Transactions
```
400 Bad Request
{
  "detail": "Period 1 is not open for contributions"
}
```

#### Invalid Amount
```
400 Bad Request
{
  "detail": "Contribution amount must be positive"
}
```

#### Cannot Carry Forward Open Period
```
409 Conflict
{
  "detail": "Source period must be CLOSED to carry forward"
}
```

## Testing

The system includes comprehensive test coverage:

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src

# Run specific test module
pytest tests/unit/test_payment_service.py -v

# Run integration tests only
pytest tests/integration/ -v
```

### Test Statistics
- **Total Tests**: 260+
- **Unit Tests**: 80+
- **Integration Tests**: 100+
- **Contract Tests**: 40+
- **Pass Rate**: 100%

### Test Categories

#### Unit Tests
- Individual service method validation
- Balance calculation accuracy
- Allocation strategy correctness
- Rounding and decimal precision

#### Integration Tests
- Complete workflow scenarios
- Multi-period balance chains
- Period transitions
- Transaction sequences

#### Contract Tests
- API request/response validation
- Status code verification
- Schema conformance
- Error handling

## Development

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Run tests
pytest tests/ -v
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Adding New Features

1. **Create Data Model** in `src/models/payment/`
2. **Implement Service Methods** in appropriate `src/services/*.py`
3. **Add API Endpoints** in `src/api/payment.py`
4. **Write Tests**:
   - Unit tests in `tests/unit/`
   - Integration tests in `tests/integration/`
   - Contract tests in `tests/contract/`
5. **Create Migration** with Alembic
6. **Update Documentation**

## Performance

Performance targets met:
- Balance sheet generation: <2 seconds (100+ transactions)
- Transaction recording: <500ms
- Period closure: <1 second
- Multi-period carry-forward: <1 second

Database queries are optimized with proper indexing and aggregation.

## Financial Precision

All monetary amounts are stored as `Decimal(10,2)` for cent-level accuracy:
- No floating-point rounding errors
- Proper handling of fractional allocations
- Remainder distribution to largest shareholder
- Verified to sum to zero (no money loss)

## Security Considerations

- Database isolation for test environment
- SQL injection prevention via SQLAlchemy ORM
- Input validation on all endpoints
- Period state management prevents invalid transitions
- Audit trail via transaction timestamps

## Future Enhancements

- Multi-currency support
- Advanced reporting and analytics
- Payment reconciliation workflows
- Automated invoice generation
- Integration with payment gateways
- Role-based access control (RBAC)
- Audit logging and compliance reporting

## Support

For issues, questions, or contributions, please open an issue in the repository.

## License

[Add appropriate license here]
