# Implementation Plan: Payment and Debt Management System

**Branch**: `003-payments-debts` | **Date**: 2025-11-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-payments-debts/spec.md`

## Summary

Implement a financial ledger system for managing payments, debts, and expenses across property owners within discrete accounting periods. Core features include:

- **Service Periods**: Discrete accounting periods (OPEN/CLOSED) as containers for all financial transactions
- **Contribution Tracking**: Record owner payments with full history and audit trail
- **Expense Management**: Track community expenses with payer attribution and flexible allocation strategies (PROPORTIONAL, FIXED_FEE, USAGE_BASED)
- **Balance Calculation**: Generate balance sheets showing each owner's debt/credit position
- **Utility Billing**: Support meter-based usage calculations for utilities
- **Data Integrity**: Ensure all allocated amounts sum to total (no money loss/creation) with remainder distribution to largest share holders

Technical approach: Extend existing SQLAlchemy ORM models with 6 new financial models (ServicePeriod, ContributionLedger, ExpenseLedger, BudgetItem, UtilityReading, ServiceCharge) within existing FastAPI service. Add financial calculation services with comprehensive test coverage. Integration with existing User and Property models ensures referential integrity.

## Technical Context

**Language/Version**: Python 3.11+ (per constitution)  
**Primary Dependencies**: FastAPI (HTTP API), SQLAlchemy (ORM), Alembic (migrations), python-telegram-bot (existing integration)  
**Storage**: SQLite (development) / suitable production replacement per constitution  
**Testing**: pytest (existing test suite structure)  
**Target Platform**: Linux server (existing deployment)  
**Project Type**: Single-project backend extension (existing structure)  
**Performance Goals**: Balance sheet generation <5 seconds (100+ transactions), transaction recording reflected in balance within 2 seconds  
**Constraints**: No performance degradation with multi-year periods; accuracy to the cent for all monetary calculations  
**Scale/Scope**: Support 10-50 property owners per instance; multi-period accounting across years

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| **YAGNI** | ✅ PASS | 6 financial models map directly to spec entities; no speculative tables; Property model enhanced only with existing share_weight field (already required for proportional allocations); no redundant fields; all fields serve explicit spec requirements |
| **KISS** | ✅ PASS | SQLAlchemy ORM used consistently; straightforward service layer pattern matches existing codebase; no complex abstractions; simple remainder distribution algorithm for rounding |
| **DRY** | ✅ PASS | Allocation logic centralized in single allocation service (PROPORTIONAL, FIXED_FEE, USAGE_BASED handled by common engine); balance calculation shared across all reports; no duplicated ledger operations |
| **Python 3.11+** | ✅ PASS | Using current Python version per constitution; type hints on all services |
| **FastAPI/SQLAlchemy/Alembic** | ✅ PASS | Extends existing tech stack; no new dependencies required (all existing) |
| **No Secrets** | ✅ PASS | No hardcoded secrets in models or services; config via environment variables |
| **MCP Context7** | ✅ PASS | No new dependencies; using documented existing libraries only |

**Gate Result**: ✅ PASS - Feature aligns with all constitution principles and project standards.

## Project Structure

### Documentation (this feature)

```text
specs/003-payments-debts/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (TBD)
├── data-model.md        # Phase 1 output (TBD)
├── quickstart.md        # Phase 1 output (TBD)
├── contracts/           # Phase 1 output (TBD)
│   └── financial-api.md # REST API contracts for financial operations
└── tasks.md             # Phase 2 output (TBD)
```

### Source Code (repository root)

Extending existing single-project structure (Option 1 - DEFAULT):

```text
src/
├── models/              # Existing: User, ClientRequest, AccessRequest, AdminConfig
│   ├── user.py
│   ├── access_request.py
│   ├── admin_config.py
│   ├── client_request.py
│   └── [NEW] payment/   # NEW: Financial ledger models
│       ├── __init__.py
│       ├── service_period.py
│       ├── contribution_ledger.py
│       ├── expense_ledger.py
│       ├── budget_item.py
│       ├── utility_reading.py
│       └── service_charge.py
│
├── services/            # Existing: NotificationService, RequestService, UserService, AdminService
│   ├── notification_service.py
│   ├── request_service.py
│   ├── user_service.py
│   ├── admin_service.py
│   └── [NEW] payment_service.py        # NEW: Core financial operations
│   └── [NEW] allocation_service.py     # NEW: Expense allocation logic
│   └── [NEW] balance_service.py        # NEW: Balance sheet calculation
│
├── api/                 # Existing: webhook, mini_app
│   ├── webhook.py
│   ├── mini_app.py
│   └── [NEW] payment.py  # NEW: Payment API endpoints
│
└── migrations/          # Existing Alembic migrations
    └── versions/
        └── [NEW] migration for financial models

tests/
├── unit/                # Existing unit tests
│   └── [NEW] test_payment_service.py
│   └── [NEW] test_allocation_service.py
│   └── [NEW] test_balance_service.py
│
├── integration/         # Existing integration tests
│   └── [NEW] test_financial_flows.py
│
└── contract/            # Existing contract tests
    └── [NEW] test_payment_endpoints.py
```

**Structure Decision**: Extend existing single-project structure with new payment submodule under models/ and three new services (payment, allocation, balance) to keep financial logic cohesive and testable while integrating seamlessly with existing User/Property models.

## Complexity Tracking

*Constitution Check: ✅ PASS - No unjustified complexity. No violations to justify.*

No complexity violations. All design decisions follow KISS, DRY, and YAGNI principles:
