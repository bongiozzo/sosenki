# Payment and Debt Management System - API Contract

**Last Updated**: 2025-11-09  
**Version**: 1.0  
**Status**: Production Ready

## API Base URL

```
http://localhost:8000/api/payments
```

## Authentication

All endpoints support Telegram user authentication via `X-User-ID` header (optional for testing).

## Response Format

All responses use JSON with the following structure:

```json
{
  "id": 123,
  "status": "OK"
}
```

Errors:

```json
{
  "detail": "Error message"
}
```

## Period Endpoints

### POST /periods

Create a new service period.

**Request:**

```json
{
  "name": "November 2025",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30"
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "name": "November 2025",
  "status": "OPEN",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "created_at": "2025-11-09T10:00:00Z"
}
```

**Errors:**

- 400 Bad Request: Invalid dates or validation failure
- 409 Conflict: Duplicate period name

---

### GET /periods

List all service periods.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "name": "November 2025",
    "status": "OPEN",
    "start_date": "2025-11-01",
    "end_date": "2025-11-30"
  },
  {
    "id": 2,
    "name": "December 2025",
    "status": "CLOSED",
    "start_date": "2025-12-01",
    "end_date": "2025-12-31"
  }
]
```

---

### GET /periods/{period_id}

Retrieve specific period.

**Response:** 200 OK

```json
{
  "id": 1,
  "name": "November 2025",
  "status": "OPEN",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30"
}
```

**Errors:**

- 404 Not Found: Period not found

---

### POST /periods/{period_id}/close

Close a service period.

**Request:**

```json
{}
```

**Response:** 200 OK

```json
{
  "id": 1,
  "name": "November 2025",
  "status": "CLOSED",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30"
}
```

**Errors:**

- 404 Not Found: Period not found
- 409 Conflict: Period already closed

---

### PATCH /periods/{period_id}/reopen

Reopen a closed period for corrections.

**Response:** 200 OK

```json
{
  "id": 1,
  "name": "November 2025",
  "status": "OPEN",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30"
}
```

**Errors:**

- 404 Not Found: Period not found
- 409 Conflict: Period already open

---

## Contribution Endpoints

### POST /periods/{period_id}/contributions

Record owner contribution.

**Request:**

```json
{
  "owner_id": 123456789,
  "amount": 500.00,
  "date": "2025-11-05",
  "comment": "Monthly payment"
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "period_id": 1,
  "owner_id": 123456789,
  "amount": "500.00",
  "date": "2025-11-05",
  "comment": "Monthly payment"
}
```

**Errors:**

- 400 Bad Request: amount <= 0 or invalid date
- 404 Not Found: Period not found
- 409 Conflict: Period is closed

---

### GET /periods/{period_id}/contributions

List all contributions for a period.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "owner_id": 123456789,
    "amount": "500.00",
    "date": "2025-11-05"
  },
  {
    "id": 2,
    "period_id": 1,
    "owner_id": 987654321,
    "amount": "500.00",
    "date": "2025-11-05"
  }
]
```

---

### GET /periods/{period_id}/owners/{owner_id}/contributions

Get contribution summary for specific owner.

**Response:** 200 OK

```json
{
  "owner_id": 123456789,
  "period_id": 1,
  "total_contributions": "500.00",
  "contribution_count": 1,
  "contributions": [
    {
      "id": 1,
      "amount": "500.00",
      "date": "2025-11-05"
    }
  ]
}
```

---

### PATCH /contributions/{contribution_id}

Edit contribution in open period.

**Request:**

```json
{
  "amount": 600.00,
  "comment": "Corrected payment"
}
```

**Response:** 200 OK

```json
{
  "id": 1,
  "amount": "600.00",
  "comment": "Corrected payment"
}
```

---

## Expense Endpoints

### POST /periods/{period_id}/expenses

Record shared expense with payer attribution.

**Request:**

```json
{
  "paid_by_owner_id": 123456789,
  "amount": 200.00,
  "payment_type": "SECURITY",
  "date": "2025-11-10",
  "vendor": "SecureGuard",
  "description": "Monthly security"
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "period_id": 1,
  "paid_by_owner_id": 123456789,
  "amount": "200.00",
  "payment_type": "SECURITY",
  "date": "2025-11-10",
  "vendor": "SecureGuard"
}
```

**Errors:**

- 400 Bad Request: amount <= 0 or invalid date
- 404 Not Found: Period not found
- 409 Conflict: Period is closed

---

### GET /periods/{period_id}/expenses

List all expenses for a period.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "paid_by_owner_id": 123456789,
    "amount": "200.00",
    "payment_type": "SECURITY",
    "vendor": "SecureGuard"
  }
]
```

---

### GET /periods/{period_id}/expenses?paid_by={owner_id}

List expenses paid by specific owner.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "paid_by_owner_id": 123456789,
    "amount": "200.00",
    "payment_type": "SECURITY"
  }
]
```

---

### PATCH /expenses/{expense_id}

Edit expense in open period.

**Request:**

```json
{
  "amount": 250.00
}
```

**Response:** 200 OK

```json
{
  "id": 1,
  "amount": "250.00"
}
```

---

## Budget Endpoints

### POST /periods/{period_id}/budget-items

Create budget item with allocation strategy.

**Request:**

```json
{
  "payment_type": "SECURITY",
  "budgeted_amount": 200.00,
  "allocation_strategy": "PROPORTIONAL"
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "period_id": 1,
  "payment_type": "SECURITY",
  "budgeted_amount": "200.00",
  "allocation_strategy": "PROPORTIONAL"
}
```

**Allocation Strategies:**

- `PROPORTIONAL`: Distribute by owner share_weight
- `FIXED_FEE`: Distribute equally to all active properties
- `USAGE_BASED`: Distribute by consumption (requires meter_type)
- `NONE`: No automatic allocation

---

### GET /periods/{period_id}/budget-items

List budget items for a period.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "payment_type": "SECURITY",
    "budgeted_amount": "200.00",
    "allocation_strategy": "PROPORTIONAL"
  }
]
```

---

## Meter Reading Endpoints

### POST /periods/{period_id}/meter-readings

Record utility meter reading.

**Request:**

```json
{
  "meter_type": "WATER",
  "start_reading": 1000,
  "end_reading": 1250
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "period_id": 1,
  "meter_type": "WATER",
  "start_reading": "1000",
  "end_reading": "1250",
  "consumption": "250"
}
```

**Errors:**

- 400 Bad Request: end_reading <= start_reading
- 404 Not Found: Period not found

---

### GET /periods/{period_id}/meter-readings

List meter readings for a period.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "meter_type": "WATER",
    "start_reading": "1000",
    "end_reading": "1250",
    "consumption": "250"
  }
]
```

---

## Service Charge Endpoints

### POST /periods/{period_id}/charges

Record direct charge to specific owner.

**Request:**

```json
{
  "owner_id": 123456789,
  "amount": 50.00,
  "description": "Repair - door lock"
}
```

**Response:** 201 Created

```json
{
  "id": 1,
  "period_id": 1,
  "owner_id": 123456789,
  "amount": "50.00",
  "description": "Repair - door lock"
}
```

**Errors:**

- 400 Bad Request: amount <= 0
- 404 Not Found: Period not found or Owner not found
- 409 Conflict: Period is closed

---

### GET /periods/{period_id}/charges

List service charges for a period.

**Response:** 200 OK

```json
[
  {
    "id": 1,
    "period_id": 1,
    "owner_id": 123456789,
    "amount": "50.00",
    "description": "Repair - door lock"
  }
]
```

---

### GET /periods/{period_id}/service-charges

Alias for above endpoint (alternate naming convention).

---

## Balance Endpoints

### GET /periods/{period_id}/balance-sheet

Generate period balance sheet.

**Response:** 200 OK

```json
{
  "period_id": 1,
  "period_name": "November 2025",
  "status": "OPEN",
  "balances": [
    {
      "owner_id": 123456789,
      "total_contributions": "500.00",
      "total_charges": "200.00",
      "balance": "300.00"
    },
    {
      "owner_id": 987654321,
      "total_contributions": "500.00",
      "total_charges": "100.00",
      "balance": "400.00"
    }
  ],
  "total_contributions": "1000.00",
  "total_charges": "300.00",
  "total_balance": "700.00"
}
```

**Balance Formula:**

```
Balance = Total Contributions - Total Charges
```

Positive balance = Owner credit (overpaid)
Negative balance = Owner debt (underpaid)

---

### GET /periods/{period_id}/balances/{owner_id}

Get balance for specific owner.

**Response:** 200 OK

```json
{
  "period_id": 1,
  "owner_id": 123456789,
  "total_contributions": "500.00",
  "total_charges": "200.00",
  "balance": "300.00"
}
```

**Errors:**

- 404 Not Found: Period or Owner not found

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 409 | Conflict (state violation) |
| 500 | Server Error |

## Validation Rules

### Periods

- `start_date` < `end_date`
- `name` is unique per year (basic validation)
- Period cannot be created with past dates (optional)

### Contributions

- `amount` > 0
- `date` within period range
- `owner_id` must exist

### Expenses

- `amount` > 0
- `date` within period range
- `paid_by_owner_id` must exist
- `payment_type` is required

### Budget Items

- `budgeted_amount` >= 0
- `allocation_strategy` is one of: PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE
- If USAGE_BASED, `meter_type` must be specified

### Meter Readings

- `end_reading` > `start_reading`
- `meter_type` is valid (WATER, ELECTRICITY, GAS, etc.)

### Service Charges

- `amount` > 0
- `owner_id` must exist

## Transaction Immutability

All transactions are immutable after period closure:

- Period is OPEN: Create, Edit, Delete allowed
- Period is CLOSED: Read-only, Edit/Delete blocked with 409 error
- To make corrections: Reopen period, edit, then close again

## Allocation Algorithm

### PROPORTIONAL

```
charge_per_owner = total_expense × (owner.share_weight / sum_of_all_share_weights)
remainder distributed to largest share holder
```

### FIXED_FEE

```
charge_per_owner = total_expense / number_of_active_properties
```

### USAGE_BASED

```
charge_per_owner = total_expense × (owner_consumption / total_consumption)
```

## Error Messages

| Error | Status | Meaning |
|-------|--------|---------|
| "Period not found" | 404 | Invalid period_id |
| "Period is closed" | 409 | Cannot modify closed period |
| "Invalid amount" | 400 | amount <= 0 |
| "Invalid date range" | 400 | date outside period |
| "Owner not found" | 404 | Invalid owner_id |
| "Validation failed" | 400 | Field validation error |

## Rate Limiting

No rate limiting implemented (add as needed for production).

## Pagination

Endpoints returning lists currently return all results. Pagination can be added:

```
GET /periods?skip=0&limit=10
```

## Versioning

Current version: 1.0
API URL: `/api/payments` (v1 implicit)
Future versions: `/api/v2/payments`, etc.

## Example Integration Flow

```bash
# 1. Create period
period_id=$(curl -X POST http://localhost:8000/api/payments/periods \
  -d '{"name": "Nov 2025", ...}' | jq .id)

# 2. Record contributions
curl -X POST http://localhost:8000/api/payments/periods/$period_id/contributions \
  -d '{"owner_id": 123, "amount": 500, ...}'

# 3. Record expenses
curl -X POST http://localhost:8000/api/payments/periods/$period_id/expenses \
  -d '{"paid_by_owner_id": 123, "amount": 200, ...}'

# 4. Create budget
curl -X POST http://localhost:8000/api/payments/periods/$period_id/budget-items \
  -d '{"payment_type": "SECURITY", "allocation_strategy": "PROPORTIONAL", ...}'

# 5. Generate balance sheet
curl -X GET http://localhost:8000/api/payments/periods/$period_id/balance-sheet

# 6. Close period
curl -X POST http://localhost:8000/api/payments/periods/$period_id/close \
  -d '{}'
```
