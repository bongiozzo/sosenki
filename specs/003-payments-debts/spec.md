# Feature Specification: Payment and Debt Management System

**Feature Branch**: `003-payments-debts`  
**Created**: 2025-11-09  
**Status**: Draft  
**Input**: User description: "As a Administrator I want to have an ability operate payments and debts among owners. I need to store history of payments and plan future periods."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Creates Service Period (Priority: P1)

An administrator sets up a new accounting period (e.g., "Годовой 2024-2025") defining a start date and end date. This period serves as the container for all financial transactions during that timeframe. The administrator can transition the period from OPEN to CLOSED status to finalize the period's accounts.

**Why this priority**: Service periods are the foundational structure for all financial records. Without being able to create and manage periods, no other financial operations are possible. This is essential infrastructure for the entire feature.

**Independent Test**: Can be fully tested by: (1) creating a new service period with name, start date, and end date, (2) verifying the period appears in the system with OPEN status, (3) confirming the period can be transitioned to CLOSED status.

**Acceptance Scenarios**:

1. **Given** an administrator is in the system, **When** they create a new service period with name "Годовой 2024-2025", start date "2024-01-01", and end date "2024-12-31", **Then** the system records the period with status OPEN and it becomes available for financial transactions.
2. **Given** a service period exists with status OPEN, **When** the administrator closes the period, **Then** the system transitions it to CLOSED status and prevents new transactions from being added to this period.
3. **Given** an administrator closes a service period, **When** the period is closed, **Then** the system calculates and displays final balances for all owners.

---

### User Story 2 - Administrator Records Contributions and Tracks Payment History (Priority: P1)

An administrator records payment contributions made by property owners to a service period. Each contribution records who paid, how much, when they paid, and optionally why. The system maintains a complete history of all contributions, allowing the administrator to view historical records and verify that payments have been received.

**Why this priority**: Recording contributions is the core operation for tracking what owners have paid. Without this capability, the system cannot calculate debts or balance sheets. This directly enables payment tracking and debt reconciliation.

**Independent Test**: Can be fully tested by: (1) recording a contribution by owner X for amount Y in period Z, (2) verifying the contribution appears in the history, (3) confirming the contribution affects the owner's balance in that period.

**Acceptance Scenarios**:

1. **Given** a service period is open, **When** an administrator records a contribution of 5000 rubles from owner "Иванчик" on 2024-06-15 with comment "Payment for maintenance", **Then** the system stores the transaction with timestamp and all details are retrievable.
2. **Given** multiple contributions exist, **When** the administrator views the contribution history for a period, **Then** all contributions are displayed in chronological order with owner name, amount, date, and comment.
3. **Given** an owner makes multiple contributions, **When** the administrator views that owner's record, **Then** the system displays cumulative contribution amount for the period.

---

### User Story 3 - Administrator Records Expenses and Associates with Payers (Priority: P1)

An administrator records expenses incurred by the organization (e.g., security guard salary, utilities, repairs). For each expense, the system captures: who paid the expense from their own pocket (paid_by_user_id), when it was paid, what type of expense it is, a description, the amount, and vendor information. This allows the administrator to properly credit the person who paid out-of-pocket and allocate these costs back to the relevant owners based on allocation strategies.

**Why this priority**: Expense tracking is essential for calculating what each owner owes. Without recording expenses and who paid them, the system cannot calculate accurate debt balances or properly credit individuals who advance payment for the community.

**Independent Test**: Can be fully tested by: (1) recording an expense paid by administrator X, (2) specifying the expense type and amount, (3) verifying the expense appears in records and reflects credit to the person who paid.

**Acceptance Scenarios**:

1. **Given** a service period is open, **When** an administrator records an expense: "ЗП Охрана" (security salary) for 15000 rubles paid by "Радионов" on 2024-07-20 from vendor "ООО Охрана", **Then** the system stores the expense and credits "Радионов" as the payer.
2. **Given** an expense exists, **When** the administrator views the expense ledger, **Then** all expenses are visible with date, type, amount, paid-by user, and description.
3. **Given** an administrator records an expense, **When** the expense is saved, **Then** the system automatically marks this as an advance payment that will be allocated back to owners based on allocation rules.

---

### User Story 4 - Administrator Allocates Expenses to Owners Using Allocation Strategies (Priority: P2)

The administrator configures how different types of expenses are allocated to owners using flexible allocation strategies. For each budget item (e.g., "Охрана"/Security), the administrator specifies: the period, expense type, budgeted amount, and allocation strategy (PROPORTIONAL, FIXED_FEE, USAGE_BASED, or NONE). Based on the selected strategy, the system calculates how much each owner owes for that expense category.

**Why this priority**: Allocation strategies are crucial for accurate debt calculation and fairness among owners. This enables dynamic, DRY (Don't Repeat Yourself) billing logic instead of static spreadsheet columns. However, the core payment recording (P1) must work first; this builds on top of it.

**Independent Test**: Can be fully tested by: (1) creating a budget item with PROPORTIONAL allocation for security expenses, (2) recording a security expense, (3) verifying each owner is charged proportionally based on their property share weight.

**Acceptance Scenarios**:

1. **Given** an administrator is configuring budget allocation, **When** they create a budget item for "Охрана" with 60000 rubles budget, allocation_strategy=PROPORTIONAL, **Then** the system stores the budget item and applies this strategy to all security expenses in that period.
2. **Given** a property owner has share_weight=2.5 and total weighted shares across all properties=10, **When** the system allocates a 10000 ruble security expense proportionally, **Then** the owner is charged 2500 rubles (2.5/10 * 10000).
3. **Given** an administrator specifies allocation_strategy=FIXED_FEE for a budget item, **When** an expense of 1000 rubles occurs, **Then** each owner with an active property (exists at period start and not deactivated) is charged an equal fixed fee, not proportional.
4. **Given** utility readings are recorded for usage-based billing, **When** the system allocates utility costs with strategy=USAGE_BASED, **Then** each owner is charged based on their consumption relative to total usage.

---

### User Story 5 - Administrator Manages Utility Readings for Usage-Based Charges (Priority: P2)

The administrator records meter readings (start and end readings) for utilities like electricity. The system calculates consumption by taking the difference between readings and multiplies by the cost-per-unit to determine the total cost. This usage-based cost is then allocated to owners according to their usage.

**Why this priority**: Usage-based billing provides accurate, fair allocation for variable costs. However, it depends on P1 infrastructure (recording expenses). This feature supports more sophisticated billing but isn't required for basic debt tracking.

**Independent Test**: Can be fully tested by: (1) recording electricity meter readings for a property, (2) calculating total cost from the difference, (3) verifying the cost appears in the owner's charges.

**Acceptance Scenarios**:

1. **Given** electricity cost per kWh is 5 rubles, **When** an administrator records meter_start_reading=1000, meter_end_reading=1500 for a property, **Then** the system calculates total_cost = 500 * 5 = 2500 rubles.
2. **Given** multiple properties have utility readings in a period, **When** the system calculates consumption, **Then** each property's cost is calculated independently and attributed correctly.
3. **Given** utility costs are recorded, **When** these are allocated to the owner of the property, **Then** the owner is charged only for their property's consumption, not shared/proportional.

---

### User Story 6 - Administrator Records Ad-Hoc Owner-Specific Charges (Priority: P2)

The administrator can apply special charges to specific owners for services not covered by standard allocation strategies. For example, "Консервация" (house preservation) charges apply only to the owner of that house and are recorded directly against their account.

**Why this priority**: Service charges handle edge cases and special circumstances (preservation costs, specific repairs). These enhance the system's flexibility but are secondary to core P1 functionality for basic payment and debt tracking.

**Independent Test**: Can be fully tested by: (1) recording a service charge for a specific owner, (2) verifying the charge appears only for that owner, (3) confirming the charge affects only that owner's debt calculation.

**Acceptance Scenarios**:

1. **Given** a service period is open, **When** an administrator records a service charge for owner "Иванчик": description="Консервация дома", amount=3000 rubles, **Then** the charge is applied only to that owner's account.
2. **Given** service charges exist for multiple owners, **When** the administrator views charges by owner, **Then** each owner sees only their own charges, not those of others.

---

### User Story 7 - Administrator Views Balance Sheet and Debt Summary (Priority: P1)

The administrator can generate a comprehensive report showing: for each owner, their total contributions, total charges/expenses allocated to them, and resulting balance (positive=credit, negative=debt). This enables the administrator to see at a glance who owes money and who has overpaid.

**Why this priority**: The balance sheet is the primary output that administrators need to manage the system. It's the mechanism for tracking debts and understanding financial status. This is essential for the feature's core value proposition.

**Independent Test**: Can be fully tested by: (1) recording contributions and expenses, (2) generating a balance report, (3) verifying calculations are correct and show each owner's debt/credit status.

**Acceptance Scenarios**:

1. **Given** a service period has contributions and allocated charges, **When** the administrator views the balance sheet, **Then** for each owner, the system displays: total contributions, total charges, and resulting balance.
2. **Given** an owner "Иванчик" contributed 10000 rubles and has 7000 rubles in charges, **When** the balance sheet is generated, **Then** "Иванчик" shows a credit/positive balance of 3000 rubles.
3. **Given** an owner "Радионов" contributed 5000 rubles and has 8000 rubles in charges, **When** the balance sheet is generated, **Then** "Радионов" shows a debt/negative balance of -3000 rubles.
4. **Given** a period is closed, **When** balances are calculated, **Then** the system displays final settled balances and prevents further modifications to that period.

---

### User Story 8 - Administrator Transitions Balances Between Service Periods (Priority: P3)

When closing a service period, the system carries forward unsettled balances (debts and credits) to the next period, establishing the opening balance for the new accounting period. This creates continuity in the ledger across multiple periods.

**Why this priority**: Period transitions are important for long-term financial continuity but can be implemented after core P1/P2 features. This addresses the stated need to "plan future periods" but is less immediately critical than establishing the basic infrastructure.

**Independent Test**: Can be fully tested by: (1) closing a service period with outstanding balances, (2) creating a new period, (3) verifying balances are carried forward correctly.

**Acceptance Scenarios**:

1. **Given** service period "2024-2025" is being closed with "Иванчик" having -3000 rubles debt, **When** a new period "2025-2026" is created, **Then** "Иванчик" starts the new period with an opening balance of -3000 rubles.
2. **Given** multiple owners have balances from a closed period, **When** balances are transitioned, **Then** each owner's balance is correctly carried forward to the next period.

---

### Edge Cases

- What happens if an administrator records a contribution or expense with a date outside the service period's date range? Should the system reject it or allow it with a warning?
- **CLARIFIED**: How does the system handle corrections or reversals? If an expense is recorded incorrectly, it can be edited in open periods with audit trail; closed periods are read-only and require period reopening or separate reversal transactions.
- What if a property's share weight changes mid-period? Should charges already allocated be recalculated, or does the change apply only to future charges?
- How does the system handle multiple expenses with different expense types on the same date? Does order of allocation matter?
- What happens to allocated charges if the allocation strategy for a budget item is changed after expenses are already recorded?
- If usage readings are missing for a period, how does the system handle calculation of usage-based charges?
- Can service charges be applied retroactively to closed periods, or only to open periods?
- **CLARIFIED**: How are rounding errors handled when allocating fractional amounts across owners? → Allocate with normal rounding to all owners, then distribute any remainder (cents) to the owner(s) with the largest share weight(s).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support creating service periods with name, start_date, end_date, and status (OPEN/CLOSED).
- **FR-002**: System MUST allow closing a service period, which calculates final balances and transitions them to the next period (if one exists). Administrators can reopen a closed period to make corrections; reopening triggers recalculation of all allocations in that period and automatic recalculation of balances carried to subsequent periods.
- **FR-003**: System MUST record contribution transactions with: service_period_id, user_id, amount, date, and optional comment.
- **FR-004**: System MUST maintain a contribution ledger for each service period showing all recorded payments from owners.
- **FR-005**: System MUST record expense transactions with: service_period_id, paid_by_user_id (who paid out-of-pocket), date, payment_type, description, amount, and vendor information.
- **FR-006**: System MUST maintain an expense ledger for each service period showing all recorded expenses and who paid them.
- **FR-007**: System MUST support creating budget items that define: period, payment_type, budgeted_cost, and allocation_strategy (PROPORTIONAL, FIXED_FEE, USAGE_BASED, or NONE).
- **FR-008**: System MUST allocate PROPORTIONAL expenses to owners based on their property's share_weight relative to total weighted shares.
- **FR-009**: System MUST allocate FIXED_FEE expenses equally to all owners with active properties in the period. An "active" property is one that exists at the service period start and has not been explicitly deactivated during the period.
- **FR-010**: System MUST support recording utility readings: property_id, service_period_id, meter_start_reading, meter_end_reading, and automatically calculate total_cost based on consumption and cost_per_unit.
- **FR-011**: System MUST allocate USAGE_BASED expenses to owners proportionally based on their property's recorded consumption.
- **FR-012**: System MUST support recording service charges that apply to a specific owner: owner_id, service_period_id, description, and amount.
- **FR-013**: System MUST generate a balance sheet report showing each owner's total contributions, total charges, and resulting balance (credit/debt) for a given service period.
- **FR-014**: System MUST persist all financial records (contributions, expenses, charges, readings) to enable historical retrieval and basic transparency. Detailed audit logging of transaction changes is deferred to a future enhancement.
- **FR-015**: System MUST ensure data consistency: all allocated charges must sum to the total expense amount (no loss or creation of money).
- **FR-016**: System MUST prevent modifications to closed service periods; closed periods are read-only for historical reference.
- **FR-017**: System MUST relate all financial records to a service period to support discrete accounting periods with proper financial closing.
- **FR-018**: System MUST link all financial records to relevant properties and owners through the User and Property models to maintain referential integrity.
- **FR-019**: System MUST allow administrators to edit recorded transactions (contributions, expenses, service charges) for open service periods. Transaction edits overwrite previous values (change history/audit trail is a future enhancement).
- **FR-020**: System MUST prevent editing of transactions in closed service periods unless the period is explicitly reopened by an administrator. When a period is reopened, all transactions become editable and all balances are recalculated upon re-closing.
- **FR-021**: System MUST handle fractional allocations in proportional and fixed-fee expense distributions by: (1) allocating amounts with normal rounding to all owners, (2) calculating any remainder in cents, (3) distributing the remainder to the owner(s) with the largest share weight(s). This ensures the sum of all allocated amounts equals the total expense amount exactly.

### Key Entities

- **User Model** (existing): Enhanced usage for financial transactions. Represents property owners and administrators. Key attributes: telegram_id, first_name, last_name, is_investor, is_administrator, is_owner, is_staff, contact_info.

- **Property Model** (new): Represents physical properties/houses. Key attributes: id, owner_id (Foreign Key to User), property_name (e.g., "1", "27", "34а"), type (e.g., "Большой", "Малый", "Охрана"), share_weight (e.g., 2.5, 1). The share_weight is critical for proportional allocations and makes the system DRY by storing this coefficient once.

- **ServicePeriod Model** (new): Central model for discrete accounting periods. Key attributes: id, name (e.g., "Годовой 2024-2025"), start_date, end_date, status (OPEN/CLOSED). All financial records are linked to a specific service period.

- **ContributionLedger Model** (new): Records owner contributions/payments. Key attributes: id, service_period_id (Foreign Key), user_id (Foreign Key), amount, date, comment.

- **ExpenseLedger Model** (new): Records expenses incurred. Key attributes: id, service_period_id (Foreign Key), paid_by_user_id (Foreign Key to User who paid), date, payment_type (e.g., "ЗП Охрана"), description, amount, vendor. The paid_by_user_id is critical for crediting individuals who advance payment.

- **BudgetItem Model** (new): Defines expense allocation rules. Key attributes: id, period (year/quarter/month identifier), payment_type (e.g., "Охрана"), budgeted_cost, allocation_strategy (PROPORTIONAL/FIXED_FEE/USAGE_BASED/NONE).

- **UtilityReading Model** (new): Records meter readings for usage-based billing. Key attributes: id, property_id (Foreign Key), service_period_id (Foreign Key), meter_start_reading, meter_end_reading, total_cost (calculated). The system calculates total_cost as: (meter_end_reading - meter_start_reading) * cost_per_unit.

- **ServiceCharge Model** (new): Represents ad-hoc owner-specific charges. Key attributes: id, owner_id (Foreign Key), service_period_id (Foreign Key), description (e.g., "Консервация дома"), amount.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can create a new service period and assign it to the system within 1 minute.
- **SC-002**: The system stores and retrieves 100% of recorded contributions and expenses without data loss.
- **SC-003**: A balance sheet report can be generated and displayed to an administrator within 5 seconds, even with 100+ transactions in the period.
- **SC-004**: Proportional and fixed-fee allocation calculations are accurate to the cent with zero money loss or creation: sum of all allocated amounts equals the total expense amount exactly (no remainder unallocated).
- **SC-005**: Administrators can record a contribution, expense, or service charge and see it reflected in the balance sheet within 2 seconds.
- **SC-006**: The system successfully prevents modifications to closed service periods (reads-only enforcement).
- **SC-007**: When a service period is closed, final balances are correctly calculated and transitioned to the next period with 100% accuracy.
- **SC-008**: Utility consumption calculations are accurate: total_cost = (meter_end_reading - meter_start_reading) * cost_per_unit.
- **SC-009**: The system supports service periods spanning 1 year or multiple years (e.g., "2024-2025") without performance degradation.
- **SC-010**: Administrators report improved ability to track and reconcile debts compared to spreadsheet-based tracking.

## Assumptions

- All dates are provided in ISO 8601 format (YYYY-MM-DD) or a consistent, configurable format.
- The cost_per_unit for utilities is stored in a configuration or application settings and is consistent within a service period.
- Property share weights are stable within a service period; mid-period changes to share_weight are out of scope for this feature (handled in a future enhancement).
- Service periods do not overlap; each owner is active in only one service period at a time.
- The term "owner" refers to individuals who own/are responsible for a property; multiple owners for a single property are not supported in this version (single owner per property).
- Currency is in rubles (₽) throughout the system, though the models are designed to be currency-agnostic.
- Allocation strategies are applied at the expense level: each recorded expense matches one budget item's allocation strategy.
- The system assumes administrator actions are trustworthy and properly authorized; detailed role-based access control is not in scope for this feature (handled by existing User authentication).

## Clarifications

### Session 2025-11-09

- Q: How should the system handle corrections to already recorded transactions? → A: Allow direct editing of recorded transactions with audit trail logging all changes.
- Q: What defines an "active" property for allocation purposes? → A: A property is active throughout the entire service period if it exists at the start of the period and hasn't been explicitly deactivated during the period.
- Q: What level of audit logging is required for compliance? → A: Audit logging is deferred as a future enhancement; MVP focuses on core functionality (data persistence and retrieval for transparency).
- Q: How should corrections be handled after a period is closed? → A: Administrators can reopen a closed period, make corrections, recalculate all balances, then close again. Balances carried to the next period are automatically recalculated.
- Q: How should fractional amounts be handled when allocating expenses across owners? → A: Allocate to all owners with normal rounding, then distribute any remainder (cents) to the owner(s) with the largest share weight(s) to ensure no money is lost or created.
