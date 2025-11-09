# Payment and Debt Management System - Quickstart Guide# Payment and Debt Management System - Quickstart Guide



**Last Updated**: 2025-11-09  **Last Updated**: 2025-11-09  

**Feature**: Payment and Debt Management System (003-payments-debts)  **Feature**: Payment and Debt Management System (003-payments-debts)  

**Status**: Production Ready**Status**: Production Ready



## Overview## Overview



The Payment and Debt Management System provides a comprehensive REST API for managing apartment community finances including contributions, expenses, budgets, allocations, meter readings, and balance sheets.The Payment and Debt Management System provides a comprehensive REST API for managing apartment community finances including contributions, expenses, budgets, allocations, meter readings, and balance sheets.



## Prerequisites## Prerequisites



- Python 3.11+- Python 3.11+  

- FastAPI running on `http://localhost:8000`- FastAPI running on `http://localhost:8000`  

- SQLite database (auto-initialized)- SQLite database (auto-initialized)  

- Telegram Bot integration enabled (for mini-app access)- Telegram Bot integration enabled (for mini-app access)  



## Quick Setup## Quick Setup



### 1. Start the Application### 1. Start the Application



```bash```bash

cd /Users/serpo/Work/SOSenkicd /Users/serpo/Work/SOSenki

uv sync  # Install dependenciesuv sync  # Install dependencies

uv run python src/main.py  # Start FastAPI serveruv run python src/main.py  # Start FastAPI server

``````



Server runs at: `http://localhost:8000`Server runs at: `http://localhost:8000`  

API docs available at: `http://localhost:8000/docs` (Swagger UI)API docs available at: `http://localhost:8000/docs` (Swagger UI)



### 2. Create Test Users### 2. Create Test Users



The system uses Telegram user IDs. For testing, use numeric IDs:The system uses Telegram user IDs. For testing, use numeric IDs like:



- Owner 1: `123456789`- Owner 1: `123456789`  

- Owner 2: `987654321`- Owner 2: `987654321`  

- Admin: `111111111`- Admin: `111111111`  



Users auto-create on first transaction.Users auto-create on first transaction.



## Common Workflows## Common Workflows



### Workflow 1: Basic Period with Contributions and Expenses### Workflow 1: Basic Period with Contributions and Expenses



#### Step 1: Create a Service Period#### Step 1: Create a Service Period



```bash```bash

curl -X POST http://localhost:8000/api/payments/periods \curl -X POST http://localhost:8000/api/payments/periods \

  -H "Content-Type: application/json" \  -H "Content-Type: application/json" \

  -d '{  -d '{

    "name": "November 2025",    "name": "November 2025",

    "start_date": "2025-11-01",    "start_date": "2025-11-01",

    "end_date": "2025-11-30"    "end_date": "2025-11-30"

  }'  }'

``````



Response:Response:

```json

```json{

{  "id": 1,

  "id": 1,  "name": "November 2025",

  "name": "November 2025",  "status": "OPEN",

  "status": "OPEN",  "start_date": "2025-11-01",

  "start_date": "2025-11-01",  "end_date": "2025-11-30"

  "end_date": "2025-11-30"}

}```

```

**Step 2: Record Owner Contributions**

#### Step 2: Record Owner Contributions

```bash

```bash# Owner 1 contributes 500

# Owner 1 contributes 500curl -X POST http://localhost:8000/api/payments/periods/1/contributions \

curl -X POST http://localhost:8000/api/payments/periods/1/contributions \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{

  -d '{    "owner_id": 123456789,

    "owner_id": 123456789,    "amount": 500.00,

    "amount": 500.00,    "date": "2025-11-05",

    "date": "2025-11-05",    "comment": "Monthly payment"

    "comment": "Monthly payment"  }'

  }'

# Owner 2 contributes 500

# Owner 2 contributes 500curl -X POST http://localhost:8000/api/payments/periods/1/contributions \

curl -X POST http://localhost:8000/api/payments/periods/1/contributions \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{

  -d '{    "owner_id": 987654321,

    "owner_id": 987654321,    "amount": 500.00,

    "amount": 500.00,    "date": "2025-11-05",

    "date": "2025-11-05",    "comment": "Monthly payment"

    "comment": "Monthly payment"  }'

  }'```

```

**Step 3: Record Shared Expenses**

#### Step 3: Record Shared Expenses

```bash

```bash# Security service ($200) - paid by Owner 1

# Security service ($200) - paid by Owner 1curl -X POST http://localhost:8000/api/payments/periods/1/expenses \

curl -X POST http://localhost:8000/api/payments/periods/1/expenses \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{

  -d '{    "paid_by_owner_id": 123456789,

    "paid_by_owner_id": 123456789,    "amount": 200.00,

    "amount": 200.00,    "payment_type": "SECURITY",

    "payment_type": "SECURITY",    "date": "2025-11-10",

    "date": "2025-11-10",    "vendor": "SecureGuard",

    "vendor": "SecureGuard",    "description": "Monthly security"

    "description": "Monthly security"  }'

  }'

# Water bill ($100) - paid by Owner 2

# Water bill ($100) - paid by Owner 2curl -X POST http://localhost:8000/api/payments/periods/1/expenses \

curl -X POST http://localhost:8000/api/payments/periods/1/expenses \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{

  -d '{    "paid_by_owner_id": 987654321,

    "paid_by_owner_id": 987654321,    "amount": 100.00,

    "amount": 100.00,    "payment_type": "UTILITIES",

    "payment_type": "UTILITIES",    "date": "2025-11-15",

    "date": "2025-11-15",    "vendor": "Water Company",

    "vendor": "Water Company",    "description": "Monthly water"

    "description": "Monthly water"  }'

  }'```

```

**Step 4: Create Budget for Proportional Allocation**

#### Step 4: Create Budget for Proportional Allocation

```bash

```bashcurl -X POST http://localhost:8000/api/payments/periods/1/budget-items \

curl -X POST http://localhost:8000/api/payments/periods/1/budget-items \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{

  -d '{    "payment_type": "SECURITY",

    "payment_type": "SECURITY",    "budgeted_amount": 200.00,

    "budgeted_amount": 200.00,    "allocation_strategy": "PROPORTIONAL"

    "allocation_strategy": "PROPORTIONAL"  }'

  }'```

```

Response:

Response:```json

{

```json  "id": 1,

{  "period_id": 1,

  "id": 1,  "payment_type": "SECURITY",

  "period_id": 1,  "budgeted_amount": "200.00",

  "payment_type": "SECURITY",  "allocation_strategy": "PROPORTIONAL"

  "budgeted_amount": "200.00",}

  "allocation_strategy": "PROPORTIONAL"```

}

```**Step 5: Generate Balance Sheet**



#### Step 5: Generate Balance Sheet```bash

curl -X GET http://localhost:8000/api/payments/periods/1/balance-sheet

```bash```

curl -X GET http://localhost:8000/api/payments/periods/1/balance-sheet

```Response shows contributions, charges, and net balance per owner:

```json

Response shows contributions, charges, and net balance per owner:{

  "period_id": 1,

```json  "period_name": "November 2025",

{  "status": "OPEN",

  "period_id": 1,  "balances": [

  "period_name": "November 2025",    {

  "status": "OPEN",      "owner_id": 123456789,

  "balances": [      "total_contributions": 500.00,

    {      "total_charges": 200.00,

      "owner_id": 123456789,      "balance": 300.00

      "total_contributions": 500.00,    },

      "total_charges": 200.00,    {

      "balance": 300.00      "owner_id": 987654321,

    },      "total_contributions": 500.00,

    {      "total_charges": 100.00,

      "owner_id": 987654321,      "balance": 400.00

      "total_contributions": 500.00,    }

      "total_charges": 100.00,  ],

      "balance": 400.00  "total_contributions": 1000.00,

    }  "total_charges": 300.00,

  ],  "total_balance": 700.00

  "total_contributions": 1000.00,}

  "total_charges": 300.00,```

  "total_balance": 700.00

}### Workflow 2: Usage-Based Billing (Meter Readings)

```

**Step 1: Record Meter Reading**

### Workflow 2: Usage-Based Billing (Meter Readings)

```bash

#### Step 1: Record Meter Readingcurl -X POST http://localhost:8000/api/payments/periods/1/meter-readings \

  -H "Content-Type: application/json" \

```bash  -d '{

curl -X POST http://localhost:8000/api/payments/periods/1/meter-readings \    "meter_type": "WATER",

  -H "Content-Type: application/json" \    "start_reading": 1000,

  -d '{    "end_reading": 1250

    "meter_type": "WATER",  }'

    "start_reading": 1000,```

    "end_reading": 1250

  }'Response:

``````json

{

Response:  "id": 1,

  "period_id": 1,

```json  "meter_type": "WATER",

{  "start_reading": "1000",

  "id": 1,  "end_reading": "1250",

  "period_id": 1,  "consumption": "250"

  "meter_type": "WATER",}

  "start_reading": "1000",```

  "end_reading": "1250",

  "consumption": "250"**Step 2: Create Usage-Based Budget**

}

``````bash

curl -X POST http://localhost:8000/api/payments/periods/1/budget-items \

#### Step 2: Create Usage-Based Budget  -H "Content-Type: application/json" \

  -d '{

```bash    "payment_type": "UTILITIES",

curl -X POST http://localhost:8000/api/payments/periods/1/budget-items \    "budgeted_amount": 100.00,

  -H "Content-Type: application/json" \    "allocation_strategy": "USAGE_BASED",

  -d '{    "meter_type": "WATER"

    "payment_type": "UTILITIES",  }'

    "budgeted_amount": 100.00,```

    "allocation_strategy": "USAGE_BASED",

    "meter_type": "WATER"**Step 3: Allocate Usage-Based Charges**

  }'

```Water bill $100 is split based on consumption:

- Owner 1: 150 units × ($100/250 total) = $60

#### Step 3: Allocate Usage-Based Charges- Owner 2: 100 units × ($100/250 total) = $40



Water bill $100 is split based on consumption:### Workflow 3: Service Charges (Direct Owner Charges)



- Owner 1: 150 units × ($100/250 total) = $60**Step 1: Record Direct Charge to Specific Owner**

- Owner 2: 100 units × ($100/250 total) = $40

```bash

### Workflow 3: Service Charges (Direct Owner Charges)curl -X POST http://localhost:8000/api/payments/periods/1/charges \

  -H "Content-Type: application/json" \

#### Step 1: Record Direct Charge to Specific Owner  -d '{

    "owner_id": 123456789,

```bash    "amount": 50.00,

curl -X POST http://localhost:8000/api/payments/periods/1/charges \    "description": "Repair - door lock"

  -H "Content-Type: application/json" \  }'

  -d '{```

    "owner_id": 123456789,

    "amount": 50.00,Response:

    "description": "Repair - door lock"```json

  }'{

```  "id": 1,

  "period_id": 1,

Response:  "owner_id": 123456789,

  "amount": "50.00",

```json  "description": "Repair - door lock"

{}

  "id": 1,```

  "period_id": 1,

  "owner_id": 123456789,**Step 2: View Owner Balance After Charge**

  "amount": "50.00",

  "description": "Repair - door lock"```bash

}curl -X GET http://localhost:8000/api/payments/periods/1/balances/123456789

``````



#### Step 2: View Owner Balance After ChargeThe balance now reflects the additional service charge.



```bash### Workflow 4: Multi-Period Balance Carry-Forward

curl -X GET http://localhost:8000/api/payments/periods/1/balances/123456789

```**Step 1: Close First Period**



The balance now reflects the additional service charge.```bash

curl -X POST http://localhost:8000/api/payments/periods/1/close \

### Workflow 4: Multi-Period Balance Carry-Forward  -H "Content-Type: application/json" \

  -d '{}'

#### Step 1: Close First Period```



```bashPeriod status becomes `CLOSED`; balances are locked.

curl -X POST http://localhost:8000/api/payments/periods/1/close \

  -H "Content-Type: application/json" \**Step 2: Create Next Period**

  -d '{}'

``````bash

curl -X POST http://localhost:8000/api/payments/periods \

Period status becomes `CLOSED`; balances are locked.  -H "Content-Type: application/json" \

  -d '{

#### Step 2: Create Next Period    "name": "December 2025",

    "start_date": "2025-12-01",

```bash    "end_date": "2025-12-31"

curl -X POST http://localhost:8000/api/payments/periods \  }'

  -H "Content-Type: application/json" \```

  -d '{

    "name": "December 2025",Returns `period_id: 2`

    "start_date": "2025-12-01",

    "end_date": "2025-12-31"**Step 3: Verify Carry-Forward Balance**

  }'

```When new period is created, opening balances from previous period are automatically carried forward. Owners with positive balances (credit) or negative balances (debt) see them in the new period.



Returns `period_id: 2`## Test Scenarios



#### Step 3: Verify Carry-Forward Balance### Test 1: Proportional Allocation with 3 Owners



When new period is created, opening balances from previous period are automatically carried forward. Owners with positive balances (credit) or negative balances (debt) see them in the new period.```bash

# Setup

## Test Scenarioscurl -X POST http://localhost:8000/api/payments/periods \

  -H "Content-Type: application/json" \

### Test 1: Proportional Allocation with 3 Owners  -d '{"name": "Test Period", "start_date": "2025-11-01", "end_date": "2025-11-30"}'

# Returns period_id: 1

```bash

# Setup# Add 3 owners with contributions

curl -X POST http://localhost:8000/api/payments/periods \for owner_id in 111111111 222222222 333333333; do

  -H "Content-Type: application/json" \  curl -X POST http://localhost:8000/api/payments/periods/1/contributions \

  -d '{"name": "Test Period", "start_date": "2025-11-01", "end_date": "2025-11-30"}'    -H "Content-Type: application/json" \

# Returns period_id: 1    -d "{\"owner_id\": $owner_id, \"amount\": 300.00, \"date\": \"2025-11-05\"}"

done

# Add 3 owners with contributions

for owner_id in 111111111 222222222 333333333; do# Record $90 security expense (Owner 1 pays)

  curl -X POST http://localhost:8000/api/payments/periods/1/contributions \curl -X POST http://localhost:8000/api/payments/periods/1/expenses \

    -H "Content-Type: application/json" \  -H "Content-Type: application/json" \

    -d "{\"owner_id\": $owner_id, \"amount\": 300.00, \"date\": \"2025-11-05\"}"  -d '{"paid_by_owner_id": 111111111, "amount": 90.00, "payment_type": "SECURITY", "date": "2025-11-10", "vendor": "Guard"}'

done

# Create proportional budget

# Record $90 security expense (Owner 1 pays)curl -X POST http://localhost:8000/api/payments/periods/1/budget-items \

curl -X POST http://localhost:8000/api/payments/periods/1/expenses \  -H "Content-Type: application/json" \

  -H "Content-Type: application/json" \  -d '{"payment_type": "SECURITY", "budgeted_amount": 90.00, "allocation_strategy": "PROPORTIONAL"}'

  -d '{"paid_by_owner_id": 111111111, "amount": 90.00, "payment_type": "SECURITY", "date": "2025-11-10", "vendor": "Guard"}'

# Verify allocation: Each owner gets $30 (90/3)

# Create proportional budgetcurl -X GET http://localhost:8000/api/payments/periods/1/balance-sheet

curl -X POST http://localhost:8000/api/payments/periods/1/budget-items \```

  -H "Content-Type: application/json" \

  -d '{"payment_type": "SECURITY", "budgeted_amount": 90.00, "allocation_strategy": "PROPORTIONAL"}'Expected: Each owner charged $30, Owner 1 owed $60 credit (paid extra $30).



# Verify allocation: Each owner gets $30 (90/3)### Test 2: Fixed-Fee Allocation

curl -X GET http://localhost:8000/api/payments/periods/1/balance-sheet

```Replace `PROPORTIONAL` with `FIXED_FEE` in budget creation.



Expected: Each owner charged $30, Owner 1 owed $60 credit (paid extra $30).Expected: Fixed amount split equally regardless of share_weight.



### Test 2: Fixed-Fee Allocation### Test 3: Error Handling - Transaction in Closed Period



Replace `PROPORTIONAL` with `FIXED_FEE` in budget creation.```bash

# Close period

Expected: Fixed amount split equally regardless of share_weight.curl -X POST http://localhost:8000/api/payments/periods/1/close -H "Content-Type: application/json" -d '{}'



### Test 3: Error Handling - Transaction in Closed Period# Try to add contribution (should fail with 409)

curl -X POST http://localhost:8000/api/payments/periods/1/contributions \

```bash  -H "Content-Type: application/json" \

# Close period  -d '{"owner_id": 123456789, "amount": 100.00, "date": "2025-11-05"}'

curl -X POST http://localhost:8000/api/payments/periods/1/close -H "Content-Type: application/json" -d '{}'```



# Try to add contribution (should fail with 409)Expected: HTTP 409 Conflict - "Period is closed"

curl -X POST http://localhost:8000/api/payments/periods/1/contributions \

  -H "Content-Type: application/json" \### Test 4: Balance Accuracy to the Cent

  -d '{"owner_id": 123456789, "amount": 100.00, "date": "2025-11-05"}'

``````bash

# Create period with amounts that test rounding

Expected: HTTP 409 Conflict - "Period is closed"curl -X POST http://localhost:8000/api/payments/periods \

  -H "Content-Type: application/json" \

### Test 4: Balance Accuracy to the Cent  -d '{"name": "Rounding Test", "start_date": "2025-11-01", "end_date": "2025-11-30"}'



```bash# Add 3 owners

# Create period with amounts that test rounding# Record $1000 expense to be split 3 ways (333.33, 333.33, 333.34)

curl -X POST http://localhost:8000/api/payments/periods \# Verify total = $1000 with no rounding errors

  -H "Content-Type: application/json" \```

  -d '{"name": "Rounding Test", "start_date": "2025-11-01", "end_date": "2025-11-30"}'

## Running the Test Suite

# Add 3 owners

# Record $1000 expense to be split 3 ways (333.33, 333.33, 333.34)```bash

# Verify total = $1000 with no rounding errors# Run all tests

```uv run pytest tests/ -v



## Running the Test Suite# Run specific test file

uv run pytest tests/integration/test_financial_flows.py -v

```bash

# Run all tests# Run with coverage

uv run pytest tests/ -vuv run pytest tests/ --cov=src/services --cov=src/api --cov-report=html



# Run specific test file# Run performance profiling (see benchmarks)

uv run pytest tests/integration/test_financial_flows.py -vuv run pytest tests/ -v -k "performance" --tb=short

```

# Run with coverage

uv run pytest tests/ --cov=src/services --cov=src/api --cov-report=html## Database Structure



# Run performance profiling (see benchmarks)Key tables:

uv run pytest tests/ -v -k "performance" --tb=short- `service_periods` - Period configuration and status

```- `contribution_ledgers` - Owner contributions

- `expense_ledgers` - Shared expenses with payer attribution

## Database Structure- `budget_items` - Allocation strategy configurations

- `meter_readings` - Utility consumption data

Key tables:- `service_charges` - Direct owner charges

- `properties` - Owner properties with share weights

- `service_periods` - Period configuration and status

- `contribution_ledgers` - Owner contributionsAll transactions are immutable once recorded (use edit endpoints if correction needed before period closes).

- `expense_ledgers` - Shared expenses with payer attribution

- `budget_items` - Allocation strategy configurations## API Documentation

- `meter_readings` - Utility consumption data

- `service_charges` - Direct owner chargesFull OpenAPI documentation available at:

- `properties` - Owner properties with share weights- **Swagger UI**: `http://localhost:8000/docs`

- **ReDoc**: `http://localhost:8000/redoc`

All transactions are immutable once recorded (use edit endpoints if correction needed before period closes).- **JSON Schema**: `http://localhost:8000/openapi.json`



## API DocumentationAll endpoints documented with request/response examples in Swagger.



Full OpenAPI documentation available at:## Troubleshooting



- **Swagger UI**: `http://localhost:8000/docs`### "Period not found" Error

- **ReDoc**: `http://localhost:8000/redoc`

- **JSON Schema**: `http://localhost:8000/openapi.json`Verify period_id is correct:

```bash

All endpoints documented with request/response examples in Swagger.curl -X GET http://localhost:8000/api/payments/periods

```

## Troubleshooting

### "Period is closed" Error

### "Period not found" Error

Only OPEN periods accept new transactions. Either:

Verify period_id is correct:1. Use a different period

2. Reopen the period (if admin): `PATCH /periods/{id}/reopen`

```bash

curl -X GET http://localhost:8000/api/payments/periods### Calculation Discrepancies

```

- Verify all transactions are in the same period

### "Period is closed" Error- Check that allocation strategy matches recorded budget_items

- Meter readings must have both start and end values

Only OPEN periods accept new transactions. Either:- Service charges don't participate in allocations



1. Use a different period### Performance Issues

2. Reopen the period (if admin): `PATCH /periods/{id}/reopen`

For periods with 100+ transactions:

### Calculation Discrepancies- Balance sheet generation: ~1-2 seconds

- Transaction recording: <500ms

- Verify all transactions are in the same period- Index queries optimized (owner_id, period_id)

- Check that allocation strategy matches recorded budget_items

- Meter readings must have both start and end values## Next Steps

- Service charges don't participate in allocations

1. **Integrate with Mini App**: Mini App frontend submits transactions via these endpoints

### Performance Issues2. **Set up CI/CD**: Deploy to production with automated backups

3. **Enable Notifications**: Configure Telegram notifications for transaction updates

For periods with 100+ transactions:4. **Multi-period Management**: Set up recurring period creation and automation



- Balance sheet generation: ~1-2 seconds## Support

- Transaction recording: <500ms

- Index queries optimized (owner_id, period_id)For issues or questions:

- Check integration tests in `tests/integration/` for examples

## Next Steps- Review contract tests in `tests/contract/` for API contracts

- See `data-model.md` for entity definitions

1. **Integrate with Mini App**: Mini App frontend submits transactions via these endpoints
2. **Set up CI/CD**: Deploy to production with automated backups
3. **Enable Notifications**: Configure Telegram notifications for transaction updates
4. **Multi-period Management**: Set up recurring period creation and automation

## Support

For issues or questions:

- Check integration tests in `tests/integration/` for examples
- Review contract tests in `tests/contract/` for API contracts
- See `data-model.md` for entity definitions
