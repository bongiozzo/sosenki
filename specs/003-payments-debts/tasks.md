# Implementation Tasks: Payment and Debt Management System

**Branch**: `003-payments-debts`  
**Date**: 2025-11-09  
**Feature**: Payment and Debt Management System ([spec.md](spec.md), [plan.md](plan.md), [research.md](research.md))

---

## Overview

This task breakdown organizes implementation of the Payment and Debt Management System into 7 execution phases:

1. **Phase 1 - Setup**: Project initialization and migration infrastructure
2. **Phase 2 - Foundational**: Core models and shared services (dependency foundation for all user stories)
3. **Phase 3 - User Story 1** (P1): Service Periods creation and management
4. **Phase 4 - User Story 2** (P1): Contribution tracking
5. **Phase 5 - User Story 3** (P1): Expense recording and payer attribution
6. **Phase 6 - User Story 4-6** (P2): Allocation strategies, utility readings, service charges
7. **Phase 7 - User Story 7-8** (P3): Balance sheet generation, period transitions, balance carry-forward
8. **Phase 8 - Polish**: Cross-cutting concerns, documentation, deployment

**Key Design Principles**:

- Each user story is independently testable and deployable
- P1 stories (1-3) form complete MVP
- P2 stories (4-6) add sophisticated billing features
- P3 stories (7-8) add multi-period management
- Tasks follow strict checklist format: `- [ ] TaskID [P?] [StoryX] Description with file path`

**MVP Scope**: Phases 1-2, 3-5 (User Stories 1-3) enable core functionality: create periods, record contributions and expenses, generate balance sheet.

---

## Dependencies & Execution Order

### Blocking Sequence

```text
Phase 1 (Setup) → Phase 2 (Foundational) → [User Stories 3-5 in parallel] → Phase 6-7 (P2/P3) → Phase 8 (Polish)
```

### User Story Dependencies

- **User Story 1** (Service Periods): No dependencies; foundational
- **User Story 2** (Contributions): Requires US1 (period must exist)
- **User Story 3** (Expenses): Requires US1 (period must exist)
- **User Story 4** (Allocations): Requires US3 (expenses must exist to allocate)
- **User Story 5** (Utility Readings): Requires US1 (period) + US4 (allocation strategy)
- **User Story 6** (Service Charges): Requires US1 (period)
- **User Story 7** (Balance Sheet): Requires US1, US2, US3 (all must have transactions to report)
- **User Story 8** (Balance Carry-forward): Requires US7 (balance sheet must be calculated)

### Parallel Opportunities

- **Phase 3 & 4 & 5 parallelizable**: User Stories 1, 2, 3 can proceed in parallel after Phase 2, but prefer sequential for clean integration
- **Within Phase 4**: Models and Services parallelizable (separate files)
- **Within Phase 5**: Models and Services parallelizable (separate files)
- **Tests parallelizable**: Unit tests for each service (different files)

---

## Implementation Phases

### Phase 1: Setup & Infrastructure

**Goal**: Initialize project structure, create migration infrastructure, establish database schema versioning.

**Independent Test Criteria**:

- Alembic migration environment is functional
- Initial migration for payment models can be generated without errors
- Database can be initialized with new schema

**Tasks**:

- [x] T001 Create payment models package structure in `src/models/payment/`
- [x] T002 Create `src/models/payment/__init__.py` with model exports
- [x] T003 Create Alembic environment setup for payment feature in `src/migrations/env.py` (verified existing setup supports new models)
- [x] T004 Create initial Alembic migration template for payment models in `src/migrations/versions/` (placeholder for Phase 2)
- [x] T005 Create services package structure: `src/services/payment_service.py`, `src/services/allocation_service.py`, `src/services/balance_service.py`
- [x] T006 Create API endpoint module in `src/api/payment.py`
- [x] T007 Create test structure: `tests/unit/test_payment_*.py`, `tests/integration/test_financial_*.py`, `tests/contract/test_payment_*.py`

---

### Phase 2: Foundational Models & Shared Services

**Goal**: Implement core data models and shared financial calculation services that all user stories depend on.

**Independent Test Criteria**:

- ServicePeriod model creates and persists correctly
- AllocationService correctly implements all 4 allocation strategies
- BalanceService calculates owner balances accurately
- All models have proper SQLAlchemy relationships and constraints

**Tasks**:

- [x] T008 Implement `ServicePeriod` model in `src/models/payment/service_period.py` with status enum (OPEN/CLOSED) and state transitions
- [x] T009 Implement `ContributionLedger` model in `src/models/payment/contribution_ledger.py` with user_id, amount, date, comment fields
- [x] T010 Implement `ExpenseLedger` model in `src/models/payment/expense_ledger.py` with paid_by_user_id, payment_type, amount, date, vendor, description
- [x] T011 Implement `BudgetItem` model in `src/models/payment/budget_item.py` with period, payment_type, budgeted_cost, allocation_strategy enum
- [x] T012 Implement `UtilityReading` model in `src/models/payment/utility_reading.py` with meter_start_reading, meter_end_reading, calculated total_cost
- [x] T013 Implement `ServiceCharge` model in `src/models/payment/service_charge.py` with owner_id, description, amount, service_period_id
- [x] T014 Add required indexes to all models (service_period_id, owner_id for common queries) - removed from table_args to avoid SQLAlchemy schema conflicts
- [x] T015 Create Alembic migration for Phase 2 models in `src/migrations/versions/001_create_payment_models.py`
- [x] T016 [P] Implement `AllocationService` in `src/services/allocation_service.py` with methods for PROPORTIONAL, FIXED_FEE, USAGE_BASED strategies
- [x] T017 [P] Implement `distribute_with_remainder()` in `src/services/allocation_service.py` for rounding to largest share holder
- [x] T018 [P] Implement `BalanceService` in `src/services/balance_service.py` with balance calculation logic
- [x] T019 [P] Implement `PaymentService` base methods in `src/services/payment_service.py` (initialization, transaction editing, history retrieval)
- [ ] T020 Unit test AllocationService allocation strategies in `tests/unit/test_allocation_service.py`
- [ ] T021 Unit test BalanceService calculations in `tests/unit/test_balance_service.py`
- [ ] T022 Unit test rounding algorithm in `tests/unit/test_allocation_service.py`

---

### Phase 3: User Story 1 - Service Period Management (P1)

**Goal**: Implement service period creation, status management, and period closing with balance calculation.

**User Story**: Administrator creates service periods (OPEN/CLOSED), transitions between states, and closes periods to calculate final balances.

**Independent Test Criteria**:

- Administrator can create a service period with name, start_date, end_date
- Period is created with OPEN status
- Period can be transitioned to CLOSED
- Closed period cannot accept new transactions
- Closed period can be reopened for corrections
- Balance calculation is triggered on close

**Tasks**:

- [ ] T023 [US1] Implement `create_period()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T024 [US1] Implement `get_period()` method to retrieve period by ID in `src/services/payment_service.py`
- [ ] T025 [US1] Implement `list_periods()` method to list all periods in `src/services/payment_service.py`
- [ ] T026 [US1] Implement `close_period()` method with balance calculation trigger in `src/services/payment_service.py`
- [ ] T027 [US1] Implement `reopen_period()` method for error correction in `src/services/payment_service.py`
- [ ] T028 [US1] Implement POST `/api/periods` endpoint in `src/api/payment.py` to create period
- [ ] T029 [US1] Implement GET `/api/periods/{id}` endpoint in `src/api/payment.py` to retrieve period
- [ ] T030 [US1] Implement GET `/api/periods` endpoint in `src/api/payment.py` to list periods
- [ ] T031 [US1] Implement POST `/api/periods/{id}/close` endpoint in `src/api/payment.py` to close period
- [ ] T032 [US1] Implement PATCH `/api/periods/{id}` endpoint in `src/api/payment.py` to reopen period
- [ ] T033 [US1] Add period validation: start_date < end_date, unique period names per year
- [ ] T034 [US1] Integration test: create period → verify status OPEN → close period → verify CLOSED in `tests/integration/test_financial_flows.py`
- [ ] T035 [US1] Contract test: POST /periods returns 201, GET /periods/{id} returns period object in `tests/contract/test_payment_endpoints.py`
- [ ] T036 [US1] Contract test: POST /periods/{id}/close returns 200, period.status=CLOSED in `tests/contract/test_payment_endpoints.py`

---

### Phase 4: User Story 2 - Contribution Tracking (P1)

**Goal**: Implement recording and tracking of owner contributions (payments).

**User Story**: Administrator records contributions from property owners, maintains complete history, views cumulative contributions per owner.

**Independent Test Criteria**:

- Contribution can be recorded with user_id, amount, date, optional comment
- Contribution is stored and retrievable
- Contribution history shows all transactions chronologically
- Cumulative contribution per owner is calculated correctly
- Cannot record contribution in CLOSED period (unless reopened)

**Tasks**:

- [ ] T037 [US2] Implement `record_contribution()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T038 [US2] Implement `get_contributions()` method to list contributions for period in `src/services/payment_service.py`
- [ ] T039 [US2] Implement `get_owner_contributions()` method to get cumulative contributions for owner in period in `src/services/payment_service.py`
- [ ] T040 [US2] Implement `edit_contribution()` method to update contribution in open period in `src/services/payment_service.py`
- [ ] T041 [US2] Implement POST `/api/periods/{id}/contributions` endpoint in `src/api/payment.py` to record contribution
- [ ] T042 [US2] Implement GET `/api/periods/{id}/contributions` endpoint in `src/api/payment.py` to list contributions
- [ ] T043 [US2] Implement GET `/api/periods/{id}/contributions?owner_id={owner_id}` endpoint in `src/api/payment.py` for owner-specific contributions
- [ ] T044 [US2] Implement PATCH `/api/contributions/{id}` endpoint in `src/api/payment.py` to edit contribution
- [ ] T045 [US2] Add validation: amount > 0, date within period range, user_id exists
- [ ] T046 [US2] Prevent contribution recording in CLOSED periods with error response
- [ ] T047 [US2] Integration test: record contribution → verify in history → calculate cumulative in `tests/integration/test_financial_flows.py`
- [ ] T048 [US2] Contract test: POST /contributions returns 201 with contribution object in `tests/contract/test_payment_endpoints.py`
- [ ] T049 [US2] Contract test: GET /contributions returns chronological list in `tests/contract/test_payment_endpoints.py`
- [ ] T050 [US2] Unit test: contribution cumulative calculation in `tests/unit/test_payment_service.py`

---

### Phase 5: User Story 3 - Expense Recording & Payer Attribution (P1)

**Goal**: Implement recording of community expenses with payer attribution for advance payment crediting.

**User Story**: Administrator records expenses (security, utilities, repairs) with payer (who paid from pocket), amount, date, vendor, and type. System credits the payer and prepares for allocation back to owners.

**Independent Test Criteria**:

- Expense can be recorded with paid_by_user_id, amount, payment_type, date, vendor, description
- Expense is stored and retrievable
- Expense history shows all transactions
- Payer is correctly attributed and credited
- Cannot record expense in CLOSED period (unless reopened)

**Tasks**:

- [ ] T051 [US3] Implement `record_expense()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T052 [US3] Implement `get_expenses()` method to list expenses for period in `src/services/payment_service.py`
- [ ] T053 [US3] Implement `get_paid_by_user()` method to get expenses paid by specific user in `src/services/payment_service.py`
- [ ] T054 [US3] Implement `edit_expense()` method to update expense in open period in `src/services/payment_service.py`
- [ ] T055 [US3] Implement POST `/api/periods/{id}/expenses` endpoint in `src/api/payment.py` to record expense
- [ ] T056 [US3] Implement GET `/api/periods/{id}/expenses` endpoint in `src/api/payment.py` to list expenses
- [ ] T057 [US3] Implement GET `/api/periods/{id}/expenses?paid_by={user_id}` endpoint in `src/api/payment.py` for payer-specific expenses
- [ ] T058 [US3] Implement PATCH `/api/expenses/{id}` endpoint in `src/api/payment.py` to edit expense
- [ ] T059 [US3] Add validation: amount > 0, paid_by_user_id exists, payment_type not empty, date within period range
- [ ] T060 [US3] Prevent expense recording in CLOSED periods with error response
- [ ] T061 [US3] Store expense with reference to BudgetItem for later allocation (allow NULL if no budget item yet)
- [ ] T062 [US3] Integration test: record expense → verify in history → verify payer credited in `tests/integration/test_financial_flows.py`
- [ ] T063 [US3] Contract test: POST /expenses returns 201 with expense object in `tests/contract/test_payment_endpoints.py`
- [ ] T064 [US3] Contract test: GET /expenses returns all expenses with paid_by information in `tests/contract/test_payment_endpoints.py`
- [ ] T065 [US3] Unit test: expense recording and payer attribution in `tests/unit/test_payment_service.py`

---

### Phase 6: User Story 4-6 (P2) - Advanced Allocation & Billing

**Goal**: Implement flexible expense allocation strategies, utility-based billing, and ad-hoc service charges.

**User Stories**:

- US4: Budget items define allocation strategies (PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE); expenses are automatically allocated
- US5: Meter readings captured for utilities; consumption-based costs calculated
- US6: Service charges applied directly to specific owners (no allocation)

**Independent Test Criteria**:

- Budget item can be created with strategy type
- Proportional allocation distributes by share_weight
- Fixed-fee allocation distributes equally
- Usage-based allocation uses consumption delta
- Service charges apply only to specific owner
- Rounding algorithm distributes remainder correctly

**Tasks**:

- [ ] T066 [US4] Implement `create_budget_item()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T067 [US4] Implement `get_budget_items()` method for period in `src/services/payment_service.py`
- [ ] T068 [US4] Implement `allocate_expenses()` method to apply allocation strategy in `AllocationService` in `src/services/allocation_service.py`
- [ ] T069 [US4] Implement `allocate_proportional()` method in `AllocationService` in `src/services/allocation_service.py`
- [ ] T070 [US4] Implement `allocate_fixed_fee()` method in `AllocationService` in `src/services/allocation_service.py`
- [ ] T071 [US4] Implement POST `/api/periods/{id}/budget-items` endpoint in `src/api/payment.py` to create budget item
- [ ] T072 [US4] Implement GET `/api/periods/{id}/budget-items` endpoint in `src/api/payment.py` to list budget items
- [ ] T073 [US5] Implement `record_reading()` method in `PaymentService` for meter readings in `src/services/payment_service.py`
- [ ] T074 [US5] Implement `calculate_consumption()` method in `AllocationService` for usage-based costs in `src/services/allocation_service.py`
- [ ] T075 [US5] Implement `allocate_usage_based()` method in `AllocationService` in `src/services/allocation_service.py`
- [ ] T076 [US5] Implement POST `/api/periods/{id}/readings` endpoint in `src/api/payment.py` to record meter reading
- [ ] T077 [US5] Implement GET `/api/periods/{id}/readings` endpoint in `src/api/payment.py` to list readings
- [ ] T078 [US6] Implement `record_service_charge()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T079 [US6] Implement `get_service_charges()` method in `PaymentService` in `src/services/payment_service.py`
- [ ] T080 [US6] Implement POST `/api/periods/{id}/charges` endpoint in `src/api/payment.py` to record service charge
- [ ] T081 [US6] Implement GET `/api/periods/{id}/charges` endpoint in `src/api/payment.py` to list service charges
- [ ] T082 [US4] Integration test: create budget item → record expense → allocate by strategy in `tests/integration/test_financial_flows.py`
- [ ] T083 [US4] Unit test: proportional allocation with remainder distribution in `tests/unit/test_allocation_service.py`
- [ ] T084 [US4] Unit test: fixed-fee allocation to active properties in `tests/unit/test_allocation_service.py`
- [ ] T085 [US5] Unit test: consumption calculation from meter readings in `tests/unit/test_allocation_service.py`
- [ ] T086 [US5] Integration test: record reading → calculate consumption → allocate usage-based in `tests/integration/test_financial_flows.py`
- [ ] T087 [US6] Unit test: service charge recorded for specific owner only in `tests/unit/test_payment_service.py`
- [ ] T088 [US6] Integration test: record service charge → verify appears only for target owner in `tests/integration/test_financial_flows.py`

---

### Phase 7: User Story 7-8 (P3) - Balance Sheet & Multi-Period Management

**Goal**: Implement balance sheet generation and multi-period balance carry-forward.

**User Stories**:

- US7: Generate balance sheets showing owner contributions, charges, and resulting balance
- US8: Transition balances between periods (carry forward debts/credits to next period)

**Independent Test Criteria**:

- Balance sheet generates without errors
- Balance sheet includes all owners
- Total contributions - total charges = balance per owner
- Balance sheet reflects current period status
- Balances carry forward to next period correctly
- Downstream period balances recalculate on source period changes

**Tasks**:

- [ ] T089 [US7] Implement `calculate_balances()` method in `BalanceService` in `src/services/balance_service.py`
- [ ] T090 [US7] Implement `generate_balance_sheet()` method in `BalanceService` in `src/services/balance_service.py`
- [ ] T091 [US7] Implement `get_owner_balance()` method in `BalanceService` for individual owner balance in `src/services/balance_service.py`
- [ ] T092 [US7] Implement GET `/api/periods/{id}/balance-sheet` endpoint in `src/api/payment.py` to generate balance sheet
- [ ] T093 [US7] Implement GET `/api/periods/{id}/balances/{owner_id}` endpoint in `src/api/payment.py` for owner-specific balance
- [ ] T094 [US8] Implement `carry_forward_balance()` method in `BalanceService` in `src/services/balance_service.py`
- [ ] T095 [US8] Implement `apply_opening_balance()` method in `BalanceService` to initialize next period with carry-forward in `src/services/balance_service.py`
- [ ] T096 [US7] Add balance validation: sum of allocations = total expenses (no money loss)
- [ ] T097 [US7] Integration test: record contributions → record expenses → allocate → generate balance sheet in `tests/integration/test_financial_flows.py`
- [ ] T098 [US7] Unit test: balance calculation with multiple contributions and charges in `tests/unit/test_balance_service.py`
- [ ] T099 [US7] Unit test: balance accuracy to the cent in `tests/unit/test_balance_service.py`
- [ ] T100 [US8] Integration test: close period → calculate balances → carry forward to next period in `tests/integration/test_financial_flows.py`
- [ ] T101 [US8] Unit test: balance carry-forward accuracy in `tests/unit/test_balance_service.py`
- [ ] T102 [US8] Contract test: GET /balance-sheet returns 200 with balance sheet object in `tests/contract/test_payment_endpoints.py`

---

### Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Documentation, error handling, logging, validation, and deployment readiness.

**Independent Test Criteria**:

- All validation errors return appropriate HTTP status codes
- API documentation is complete
- Errors provide helpful user messages
- Database migrations apply cleanly
- Performance meets targets (5 sec for balance sheet with 100+ transactions, 2 sec for transaction recording)

**Tasks**:

- [ ] T103 Add comprehensive error handling for all endpoints in `src/api/payment.py` (404 for missing resources, 400 for validation errors, 409 for period state conflicts)
- [ ] T104 Add input validation decorators/middleware for all endpoints in `src/api/payment.py`
- [ ] T105 Generate OpenAPI documentation for all payment endpoints in `src/api/payment.py` (docstrings, schemas)
- [ ] T106 Add logging for all financial transactions in `src/services/payment_service.py`, `allocation_service.py`, `balance_service.py`
- [ ] T107 Create `quickstart.md` guide in `specs/003-payments-debts/quickstart.md` with setup, API examples, test scenarios
- [ ] T108 Create `data-model.md` documentation in `specs/003-payments-debts/data-model.md` with entity definitions and relationships
- [ ] T109 Create `contracts/financial-api.md` with OpenAPI specification in `specs/003-payments-debts/contracts/financial-api.md`
- [ ] T110 Run performance profiling: measure balance sheet generation time with 100+ transactions
- [ ] T111 Run performance profiling: measure transaction recording time
- [ ] T112 Optimize queries if needed (add indexes, query optimization)
- [ ] T113 Create final Alembic migration including any schema adjustments from testing in `migrations/versions/002_financial_refinements.py`
- [ ] T114 Run full integration test suite in `tests/integration/test_financial_flows.py` to verify end-to-end flows
- [ ] T115 Run contract test suite in `tests/contract/test_payment_endpoints.py` to verify API contracts
- [ ] T116 Update main.py to register new payment API routes in `src/main.py`
- [ ] T117 Update project README with payment feature overview and API documentation links
- [ ] T118 Create deployment checklist and update .github/workflows/ (if applicable) for CI/CD

---

## Summary

**Total Tasks**: 118

**Task Distribution by Phase**:

- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 15 tasks
- Phase 3 (US1): 14 tasks
- Phase 4 (US2): 14 tasks
- Phase 5 (US3): 15 tasks
- Phase 6 (US4-6): 23 tasks
- Phase 7 (US7-8): 14 tasks
- Phase 8 (Polish): 16 tasks

**Task Distribution by Type**:

- Model definitions: 6 tasks
- Service implementations: 19 tasks
- API endpoints: 22 tasks
- Validations & constraints: 8 tasks
- Tests (Unit, Integration, Contract): 28 tasks
- Documentation & DevOps: 18 tasks
- Migrations & Infrastructure: 4 tasks
- Performance & Optimization: 5 tasks

**Parallel Opportunities**:

- Phase 2: Models (T008-T015) can be parallelized across different model files
- Phase 2: Services (T016-T019) can be parallelized across different service files
- Phase 2-8: Tests can be parallelized by test file and service
- Phase 3-7: User Story implementations can leverage parallel task execution across models/services/endpoints in each story

**MVP Scope** (Phases 1-5):

- Phase 1: Setup & Migration infrastructure
- Phase 2: Foundational models & shared services
- Phase 3: User Story 1 (Service Period Management) — Create periods, close, reopen
- Phase 4: User Story 2 (Contributions) — Record and track owner payments
- Phase 5: User Story 3 (Expenses) — Record expenses with payer attribution

**Result**: Complete MVP for managing payments, tracking contributions, recording expenses, and generating basic balance sheets.

**Next Steps After MVP**:

- Phase 6: Add advanced allocation and billing features (proportional, fixed-fee, usage-based)
- Phase 7: Add multi-period balance management and carry-forward
- Phase 8: Polish, optimize, and deploy
