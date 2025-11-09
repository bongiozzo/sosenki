# Data Model Documentation

Comprehensive documentation of all financial data models in the SOSenki Payment Management System.

## Core Models

### ServicePeriod
Represents a financial period (month, quarter, etc.) for grouping transactions and calculations.

**Table**: `service_periods`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique period identifier |
| `name` | String(100) | ✓ | Period name (e.g., "November 2025") |
| `start_date` | Date | ✓ | Period start date (inclusive) |
| `end_date` | Date | ✓ | Period end date (inclusive) |
| `status` | Enum | ✓ | Status: OPEN or CLOSED |
| `description` | String(255) | - | Optional period description |
| `closed_at` | DateTime | - | Timestamp when period was closed |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `start_date` must be before `end_date`
- `name` must be unique across all periods
- Status can only transition: OPEN → CLOSED → OPEN

**Relationships**:
- Has many: `ContributionLedger`
- Has many: `ExpenseLedger`
- Has many: `ServiceCharge`
- Has many: `BudgetItem`
- Has many: `UtilityReading`

**Example Usage**:
```python
period = ServicePeriod(
    name="November 2025",
    start_date=date(2025, 11, 1),
    end_date=date(2025, 11, 30),
    status=PeriodStatus.OPEN,
    description="Monthly operational period"
)
```

---

### ContributionLedger
Records owner payments and contributions to the community fund.

**Table**: `contribution_ledgers`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique transaction identifier |
| `service_period_id` | Integer (FK) | ✓ | Reference to ServicePeriod |
| `user_id` | Integer (FK) | ✓ | Owner/user making contribution |
| `amount` | Decimal(10,2) | ✓ | Contribution amount in currency units |
| `date` | DateTime | ✓ | Date of contribution |
| `comment` | String(255) | - | Optional notes (e.g., "January payment", "Opening balance") |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `amount` must be positive (> 0)
- `date` should be within period range (but not enforced)
- Foreign key constraint: `service_period_id` must reference valid ServicePeriod
- Foreign key constraint: `user_id` must reference valid User

**Indexes**:
- `(service_period_id, user_id)` - For querying contributions by period and owner

**Relationships**:
- Belongs to: `ServicePeriod`
- Belongs to: `User`

**Financial Purpose**:
- Represents income to the community fund
- Used for balance sheet: Contributions are added to owner balance
- Sum of all contributions should match allocated expenses for balanced period

**Example Usage**:
```python
contrib = ContributionLedger(
    service_period_id=1,
    user_id=5,
    amount=Decimal("1000.00"),
    date=datetime(2025, 11, 15),
    comment="November monthly payment"
)
```

---

### ExpenseLedger
Records community expenses and tracks who paid them (payer attribution).

**Table**: `expense_ledgers`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique transaction identifier |
| `service_period_id` | Integer (FK) | ✓ | Reference to ServicePeriod |
| `paid_by_user_id` | Integer (FK) | ✓ | Owner who paid the expense |
| `amount` | Decimal(10,2) | ✓ | Expense amount |
| `payment_type` | String(100) | ✓ | Category (e.g., "Maintenance", "Utilities") |
| `vendor` | String(255) | - | Vendor/supplier name |
| `description` | String(500) | - | Detailed description |
| `date` | DateTime | ✓ | Date of expense |
| `budget_item_id` | Integer (FK) | - | Reference to BudgetItem (if tracked) |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `amount` must be positive (> 0)
- `payment_type` must be non-empty
- Foreign key constraint: `service_period_id` must reference valid ServicePeriod
- Foreign key constraint: `paid_by_user_id` must reference valid User
- Optional foreign key: `budget_item_id` references BudgetItem

**Indexes**:
- `(service_period_id, paid_by_user_id)` - For querying expenses by period and payer

**Relationships**:
- Belongs to: `ServicePeriod`
- Belongs to: `User` (via `paid_by_user_id`)
- Belongs to: `BudgetItem` (optional)

**Financial Purpose**:
- Represents outflow from community fund
- Payer is credited for advance payment (balance increases)
- Amount should be allocated back to all owners per allocation strategy
- Total expenses must equal total allocated charges when balanced

**Example Usage**:
```python
expense = ExpenseLedger(
    service_period_id=1,
    paid_by_user_id=2,
    amount=Decimal("5000.00"),
    payment_type="Maintenance",
    vendor="ABC Maintenance Co",
    description="Monthly building maintenance and repairs",
    date=datetime(2025, 11, 10)
)
```

---

### ServiceCharge
Represents per-owner charges (allocated expenses, fees, penalties, etc.).

**Table**: `service_charges`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique charge identifier |
| `service_period_id` | Integer (FK) | ✓ | Reference to ServicePeriod |
| `user_id` | Integer (FK) | ✓ | Owner subject to charge |
| `description` | String(255) | ✓ | Charge description (e.g., "Maintenance allocation", "Late fee") |
| `amount` | Decimal(10,2) | ✓ | Charge amount |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `amount` must be positive (> 0)
- `description` must be non-empty
- Foreign key constraint: `service_period_id` must reference valid ServicePeriod
- Foreign key constraint: `user_id` must reference valid User

**Indexes**:
- `(service_period_id, user_id)` - For querying charges by period and owner

**Relationships**:
- Belongs to: `ServicePeriod`
- Belongs to: `User`

**Financial Purpose**:
- Represents outflow for specific owner
- Reduces owner's balance (becomes a debt if not covered by contributions)
- Typically created by allocation strategies or as opening balance from previous period
- Can be used for penalties, maintenance fees, or carried-forward debts

**Creation Methods**:
1. Allocation strategy (proportional, fixed-fee, usage-based)
2. Opening balance from previous period (negative balance carries as charge)
3. Manual creation (administrative fee)

**Example Usage**:
```python
charge = ServiceCharge(
    service_period_id=1,
    user_id=3,
    description="Proportional maintenance allocation",
    amount=Decimal("500.00")
)
```

---

### BudgetItem
Categorizes and tracks budgeted expenses within a period.

**Table**: `budget_items`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique budget item identifier |
| `service_period_id` | Integer (FK) | ✓ | Reference to ServicePeriod |
| `payment_type` | String(100) | ✓ | Expense category (e.g., "Maintenance") |
| `budgeted_cost` | Decimal(10,2) | ✓ | Estimated/budgeted amount |
| `allocation_strategy` | String(50) | ✓ | Strategy: PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE |
| `description` | String(500) | - | Optional description |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `budgeted_cost` must be positive (> 0)
- `allocation_strategy` must be one of: PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE
- Foreign key constraint: `service_period_id` must reference valid ServicePeriod

**Relationships**:
- Belongs to: `ServicePeriod`
- Has many: `ExpenseLedger` (via `budget_item_id`)

**Allocation Strategies**:
| Strategy | Description | Use Case |
|----------|-------------|----------|
| PROPORTIONAL | Divide by ownership percentage | Maintenance, utilities |
| FIXED_FEE | Equal distribution to all owners | Management fees |
| USAGE_BASED | Based on meter readings | Water, electricity |
| NONE | No automatic allocation | Manual/one-time costs |

**Example Usage**:
```python
budget = BudgetItem(
    service_period_id=1,
    payment_type="Maintenance",
    budgeted_cost=Decimal("5000.00"),
    allocation_strategy="PROPORTIONAL",
    description="Monthly building maintenance"
)
```

---

### UtilityReading
Tracks consumption-based costs (water, electricity, gas, etc.).

**Table**: `utility_readings`

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer (PK) | ✓ | Unique reading identifier |
| `service_period_id` | Integer (FK) | ✓ | Reference to ServicePeriod |
| `meter_name` | String(255) | ✓ | Meter identifier (e.g., "Water Meter A", "Electricity") |
| `meter_start_reading` | Decimal | ✓ | Starting meter value |
| `meter_end_reading` | Decimal | ✓ | Ending meter value |
| `calculated_total_cost` | Decimal(10,2) | ✓ | Total cost for consumption |
| `unit` | String(50) | - | Unit of measurement (m³, kWh, etc.) |
| `description` | String(500) | - | Optional notes |
| `recorded_at` | DateTime | ✓ | When reading was recorded |
| `created_at` | DateTime | ✓ | Timestamp when created |
| `updated_at` | DateTime | ✓ | Timestamp when last updated |

**Constraints**:
- `meter_end_reading` must be >= `meter_start_reading`
- `calculated_total_cost` must be positive (> 0)
- Foreign key constraint: `service_period_id` must reference valid ServicePeriod

**Relationships**:
- Belongs to: `ServicePeriod`

**Consumption Calculation**:
```
consumption = meter_end_reading - meter_start_reading
cost_per_unit = calculated_total_cost / consumption
```

**Example Usage**:
```python
reading = UtilityReading(
    service_period_id=1,
    meter_name="Water Meter A",
    meter_start_reading=Decimal("1000"),
    meter_end_reading=Decimal("1150"),
    calculated_total_cost=Decimal("750.00"),
    unit="m³",
    description="November water consumption"
)
```

---

## Financial Calculation Models

### Balance Calculation
```
Balance = Total Contributions - (Total Expenses + Total Charges)
```

**Positive Balance**: Owner has credit (is owed money)
**Negative Balance**: Owner has debt (owes money)
**Zero Balance**: Settled

### Period Validation
```
Total Contributions ≈ Total Expenses + Sum(All Charges)
(Within rounding to nearest cent)
```

This ensures no money is lost in allocation process.

### Allocation Formulas

#### Proportional Allocation
```
owner_charge = (total_expense * owner_percentage) rounded
Remainder distributed to largest shareholder
```

#### Fixed Fee Allocation
```
owner_charge = total_expense / number_of_active_owners
Remainder distributed to first owner
```

#### Usage-Based Allocation
```
consumption = meter_end_reading - meter_start_reading
cost_per_unit = total_cost / total_consumption
owner_charge = owner_consumption * cost_per_unit rounded
```

---

## Data Relationships Diagram

```
ServicePeriod (1) ─┬─ (Many) ─→ ContributionLedger ─→ User
                   ├─ (Many) ─→ ExpenseLedger ─→ User
                   ├─ (Many) ─→ ServiceCharge ─→ User
                   ├─ (Many) ─→ BudgetItem
                   └─ (Many) ─→ UtilityReading

User (1) ─┬─ (Many) ─→ ContributionLedger
          ├─ (Many) ─→ ExpenseLedger (via paid_by_user_id)
          └─ (Many) ─→ ServiceCharge
```

---

## Transaction Flow Examples

### Monthly Payment Workflow
1. **Create Period**: `ServicePeriod` (Nov 2025, OPEN)
2. **Record Contributions**: Multiple `ContributionLedger` entries
3. **Record Expenses**: Multiple `ExpenseLedger` entries (with payer)
4. **Create Budget Items**: `BudgetItem` with allocation strategy
5. **Allocate Expenses**: Generate `ServiceCharge` entries via strategy
6. **Generate Balance Sheet**: Query for totals and calculate balances
7. **Close Period**: Set status to CLOSED, calculate final balances
8. **Carry Forward**: Create next period with opening balances

### Proportional Allocation Example
```
Period: Nov 2025
Owners: Alice (50%), Bob (30%), Charlie (20%)

ExpenseLedger:
- Maintenance: $5000 (paid by Alice)
- Utilities: $3000 (paid by Bob)

BudgetItem (PROPORTIONAL):
- Maintenance → 50% to each owner
- Utilities → 50% to each owner

ServiceCharge results:
- Alice: (5000*0.5 + 3000*0.5) = $4000
- Bob: (5000*0.3 + 3000*0.3) = $2400
- Charlie: (5000*0.2 + 3000*0.2) = $1600

Total: $8000 (matches total expenses)
```

### Multi-Period Balance Carry-Forward Example
```
Period 1 (Oct 2025) - CLOSED
- Alice: +$500 (credit)
- Bob: -$300 (debt)
- Charlie: $0 (balanced)

Carry Forward to Period 2 (Nov 2025):

Opening Transactions (Period 2):
- ContributionLedger: Alice $500 (opening balance)
- ServiceCharge: Bob $300 (opening debt)

Period 2 Starting Balances:
- Alice: +$500 (before new transactions)
- Bob: -$300 (before new transactions)
- Charlie: $0 (before new transactions)
```

---

## Performance Considerations

### Indexing Strategy
- Primary keys on all tables
- Foreign key indexes for joins
- Composite indexes for common queries:
  - `(service_period_id, user_id)` on ContributionLedger
  - `(service_period_id, paid_by_user_id)` on ExpenseLedger
  - `(service_period_id, user_id)` on ServiceCharge

### Query Optimization
- Aggregate queries use `GROUP BY` with `SUM()`
- Period queries filtered by `service_period_id` first
- Avoid fetching all users unless needed for balance sheet

### Decimal Precision
- All monetary amounts: `Decimal(10,2)` (max $99,999.99)
- Preserved through all calculations
- Rounding applied at final allocation only
- No floating-point arithmetic

---

## Constraints and Validations

### Data Integrity
- No orphaned transactions (FK constraints)
- Period dates must be logical (start < end)
- Amounts must be positive
- Status transitions follow state machine

### Business Rules
- Can't record transactions in CLOSED period (except opening)
- Can't close period with open period existing
- Balance sheet must sum to approximately zero
- Allocations must not lose money

### Audit Trail
- All timestamps tracked (created_at, updated_at)
- Transaction immutability (no direct updates)
- Comments preserved (e.g., "Opening balance")
- Period closed_at timestamp
