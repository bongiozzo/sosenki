# Research & Architecture: Payment and Debt Management System

**Phase**: 0 (Research & Requirements Validation)  
**Date**: 2025-11-09  
**Status**: Complete

## Executive Summary

This document consolidates architectural research, design patterns, and resolved clarifications for the Payment and Debt Management System. All unknowns from the specification have been resolved through best practices research and architecture design decisions aligned with project constitution and constraints.

---

## Research Findings

### 1. Discrete Accounting Periods Pattern

**Decision**: Implement ServicePeriod model as a state machine (OPEN ↔ CLOSED).

**Rationale**:
- Aligns with existing financial accounting practices (periodic closing, balance forward)
- Simplifies data organization and audit trails
- Enables clean handling of multi-year scenarios
- Matches "discrete periods" requirement from spec

**Alternatives Considered**:
- Continuous ledger (single table, no periods) — Rejected: makes year-end closing and balance forward complex; no natural audit boundary
- Date-based implicit periods — Rejected: requires computation to determine period boundaries; no explicit closure/finality

**Implementation Pattern**: ServicePeriod model with status transitions (OPEN → CLOSED). When transitioning CLOSED → OPEN, all dependent balances must be recalculated.

---

### 2. Expense Allocation Strategies

**Decision**: Implement allocation engine supporting 4 strategies: PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE.

**Rationale**:
- Covers all documented expense types in requirement (security fees, utilities, maintenance)
- Reduces need for manual calculations
- Maintains DRY principle: single allocation engine handles all strategies
- PROPORTIONAL: fair distribution by property share weight
- FIXED_FEE: equal distribution to all active owners
- USAGE_BASED: consumption-based for utilities
- NONE: service charges/ad-hoc with no allocation

**Alternatives Considered**:
- Hard-code allocation logic per expense type — Rejected: reduces flexibility; violates DRY; maintenance burden
- Spreadsheet-based calculations — Rejected: out of scope (system-driven allocation required)

---

### 3. Rounding & Fractional Cent Handling

**Decision**: Allocate amounts with normal rounding to all owners; distribute remainder to largest share holder(s).

**Rationale**:
- Ensures no money is lost/created (sum of allocations = total expense exactly)
- Predictable and auditable: largest share holder bears fractional burden (fair as main contributor)
- Standard accounting practice for periodic settlements
- Avoids floating-point precision issues

**Alternatives Considered**:
- Banker's rounding (round half to even) — Rejected: small variance in totals unacceptable in financial systems
- Round down universally, leave remainder unallocated — Rejected: violates FR-015 (data consistency)
- Store as integer cents only — Deferred: may implement in future for absolute precision; current approach sufficient for MVP

---

### 4. Transaction Editing & Audit Trail

**Decision**: Allow direct editing of transactions in OPEN periods; prevent editing in CLOSED periods (unless reopened).

**Rationale**:
- Balances immediate correction capability for administrative errors
- CLOSED periods protected from accidental modification
- Reopening capability (with automatic recalculation) supports correcting closed periods without losing history
- Defers comprehensive audit logging to future enhancement (MVP doesn't require full change history)

**Alternatives Considered**:
- Immutable transactions + reversal-only workflow — Rejected: complex for operators; harder to correct simple typos
- No editing, spreadsheet reconciliation — Rejected: defeats system purpose
- Comprehensive audit trail (before/after, who, when) — Deferred to Phase 2 (not MVP requirement)

---

### 5. Active Property Definition

**Decision**: A property is "active" for a period if it exists at the period start and has not been explicitly deactivated.

**Rationale**:
- Simplifies calculation logic: no per-transaction activation checks
- Matches business model: properties/owners are typically stable across periods
- Explicit deactivation provides clear operator control
- Reduces computational overhead

**Alternatives Considered**:
- Active = has recorded transactions in period — Rejected: circular dependency; requires tracking transactions to determine allocation recipients
- Active = explicitly marked per period — Rejected: requires manual setup overhead; business doesn't change that frequently
- Active = lifetime (never deactivate) — Acceptable but less flexible; current approach is backward compatible

---

### 6. Period Reopening for Corrections

**Decision**: Allow administrators to reopen CLOSED periods, make corrections, and re-close with automatic balance recalculation.

**Rationale**:
- Supports real-world scenario: discovery of errors after period close
- Maintains data integrity: all downstream balances recalculated
- Cleaner than manual cross-period adjustments
- Aligns with financial best practices (period reopening for error correction)

**Alternatives Considered**:
- Immutable closed periods; corrections via next period's reversal transaction — Rejected: creates audit confusion; harder to reconcile
- Manual spreadsheet adjustment outside system — Rejected: defeats audit trail purpose
- Multi-period rebalancing engine — Deferred to future enhancement if needed

---

### 7. Data Model Design

**Decision**: 6 new financial models (ServicePeriod, ContributionLedger, ExpenseLedger, BudgetItem, UtilityReading, ServiceCharge) extending User/Property models.

**Rationale**:
- YAGNI compliance: each model serves explicit spec requirements
- DRY: shared User/Property models eliminate duplication
- Referential integrity: foreign keys maintain data consistency
- Separation of concerns: financial logic isolated from user management

**Alternatives Considered**:
- Single unified "Transaction" table with type column — Rejected: contributions and expenses have different attributes (paid_by_user_id only on expenses); separate tables clearer
- Add all financial fields to User model — Rejected: violates single responsibility; creates user model bloat
- Use existing AccessRequest/ClientRequest for ledger entries — Rejected: different domain; mixing concerns

**Design follows Constitution YAGNI Rule**:
- Every table maps to spec requirement
- Every column has explicit usage
- No speculative/future fields
- Share_weight already exists in Property model (reused)
- No redundant timestamp fields

---

### 8. API Design (REST Endpoints)

**Decision**: RESTful API endpoints following FastAPI patterns, organized by resource type.

**Core Endpoints** (by priority):

P1: Service Periods, Contributions, Expenses, Reporting
- POST /api/periods — Create period
- GET /api/periods/{id} — Get period details
- POST /api/periods/{id}/close — Close period
- PATCH /api/periods/{id} — Reopen period
- POST /api/periods/{id}/contributions — Record contribution
- POST /api/periods/{id}/expenses — Record expense
- GET /api/periods/{id}/balance-sheet — Generate balance sheet

P2: Budget, Allocations, Utility Readings, Service Charges
- POST /api/periods/{id}/budget-items — Create budget item
- POST /api/periods/{id}/readings — Record meter reading
- POST /api/periods/{id}/charges — Record service charge

**Rationale**:
- Aligns with existing API patterns in webhook.py and mini_app.py
- Follows RESTful conventions (resource-based, HTTP methods)
- Enables incremental implementation (P1 endpoints first)
- Clear separation of concerns (each resource has CRUD)

---

### 9. Service Layer Architecture

**Decision**: Three core services (PaymentService, AllocationService, BalanceService) with clear responsibilities.

**Services**:

PaymentService:
- record_contribution(period_id, user_id, amount, date, comment) → ContributionLedger
- record_expense(period_id, paid_by_user_id, payment_type, amount, date, vendor, description) → ExpenseLedger
- record_service_charge(period_id, owner_id, description, amount) → ServiceCharge
- edit_transaction(transaction_type, transaction_id, updates) → Transaction
- get_transaction_history(period_id) → List[Transaction]

AllocationService:
- allocate_expense(expense: ExpenseLedger, budget_item: BudgetItem) → List[OwnerCharge]
- apply_all_allocations(period: ServicePeriod) → None (recalculate all charges)

BalanceService:
- calculate_balance(period: ServicePeriod, owner: User) → BalanceSheetRow
- calculate_all_balances(period: ServicePeriod) → BalanceSheet
- carry_forward_balance(from_period, to_period, owner) → None

**Rationale**:
- DRY: allocation logic centralized; no duplication across endpoints
- Testability: each service independently testable
- Maintainability: clear separation of concerns
- Extensibility: new allocation strategies added to AllocationService only

---

### 10. Testing Strategy

**Decision**: Test-first approach with unit, integration, and contract tests per project constitution.

**Test Scope**:

Unit Tests:
- Service logic isolation: allocation_distribute_with_remainder, balance_calculations, date validations

Integration Tests:
- Multi-service workflows: record_expense → allocate → balance, close_period → carry_forward

Contract Tests:
- API behavior: POST /contributions returns 201, PATCH closed-period returns 403, balance-sheet totals match

**Rationale**:
- Constitution requires test-first approach
- Supports confidence in financial calculations (high precision requirements)
- Enables safe refactoring

---

## Resolved Clarifications

All 5 clarifications from `/speckit.clarify` are embedded in design decisions above:

| # | Clarification | Resolution | Section |
|---|---------------|-----------|---------|
| 1 | Transaction editing | Direct editing in OPEN periods | Section 4 |
| 2 | Active property | Exists at period start, not deactivated | Section 5 |
| 3 | Audit logging | Deferred to Phase 2 (basic persistence sufficient for MVP) | Section 4 |
| 4 | Period reopening | Support reopening CLOSED periods for corrections | Section 6 |
| 5 | Rounding strategy | Distribute remainder to largest share holder(s) | Section 3 |

---

## Architecture Decisions Summary

| Decision | Chosen Approach | Justification |
|----------|-----------------|--------------|
| Discrete Periods | State machine (OPEN/CLOSED) with transitions | Industry standard; supports audit; enables balance forward |
| Allocation Engine | Strategy pattern with 4 implementations | DRY; flexible; extensible |
| Rounding | Distribute remainder to largest share holder | No money loss; auditable; accounting best practice |
| Transaction Editing | Direct edit in OPEN, prevent in CLOSED | Admin efficiency; data integrity protection |
| Active Property | Period-start presence + explicit deactivation | Reduces overhead; flexible; aligns with business |
| Period Reopening | Support CLOSED → OPEN transition | Real-world error correction; maintains integrity |
| Data Model | 6 new + 2 extended models | YAGNI compliant; covers spec requirements |
| API Style | RESTful with FastAPI patterns | Aligns with existing codebase; familiar patterns |
| Services | 3 core (Payment, Allocation, Balance) | Clear separation; testable; extensible |
| Testing | Unit + Integration + Contract | Ensures reliability; supports refactoring |

---

## Known Unknowns (Deferred to Implementation)

These items are suitable for planning/implementation phase and don't block design:

1. **UI Implementation**: Telegram Mini App forms for recording transactions (design template/flow)
2. **Performance Tuning**: Index strategy for large periods (profiling-driven)
3. **Error Messages**: User-facing error text for validation failures (UX polish)
4. **Comprehensive Audit Trail**: Change history logging with before/after values (future enhancement)
5. **Data Retention Policy**: Archive/delete closed periods after N years (operational decision)
6. **Scalability Tests**: Performance benchmarks with 100+ owners, 1000+ transactions (infrastructure decision)

---

## Next Phase

Proceed to **Phase 1 (Design & Contracts)** to generate:
- data-model.md with detailed entity definitions and relationships
- contracts/financial-api.md with OpenAPI specification
- quickstart.md with setup and usage guide
- Updated agent context files
