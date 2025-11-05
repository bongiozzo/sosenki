# Implementation Plan: Welcome Mini App for Approved Users

**Branch**: `002-welcome-mini-app` | **Date**: 2025-11-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-welcome-mini-app/spec.md`

## Summary

Extend the client request approval workflow (001-request-approval) to deliver newly approved clients a Telegram Mini App experience. Upon administrator approval, clients receive a Welcome message with a button to open the SOSenki Mini App—a minimalistic, Apple-inspired web application with nature-inspired colors (pine, water, sand). The Mini App verifies user registration status at load time: registered users see a welcome message and main navigation menu (Rule, Pay, Invest); non-registered users see an "Access is limited" message with instructions to send `/request`. This feature bridges the approval process and core feature access, providing the primary UX entry point for all approved clients.

## Technical Context

**Language/Version**: Python 3.11+ (per constitution)  
**Primary Dependencies**: FastAPI (API serving), python-telegram-bot (Telegram integration), Telegram Web App API (Mini App client-side)  
**Storage**: SQLite (development) + SQLAlchemy ORM, Alembic migrations (per constitution)  
**Testing**: pytest + pytest-asyncio for async tests, contract tests for API endpoints  
**Target Platform**: Web browser (Telegram Mini App running within Telegram client) + Python backend server  
**Project Type**: Web application (backend FastAPI service + frontend Mini App HTML/CSS/JavaScript)  
**Performance Goals**: <5 seconds for approval notification delivery, <3 seconds for Mini App load, <500ms for menu interactions  
**Constraints**: Telegram Mini App context isolation (no direct database access from client), registration verification must be atomic and accurate (100% correctness), graceful error handling for network failures  
**Scale/Scope**: Initial scope: newly approved clients per approval cycle (assume 1-100 per day in MVP), no bulk operations, single-user interaction model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance

| Principle | Status | Verification |
|-----------|--------|--------------|
| **YAGNI** | ✅ PASS | Feature scope limited to: approval notification + Mini App registration check + menu display. No bulk operations, no advanced settings, no future feature scaffolding. Menu items (Rule, Pay, Invest) are navigation stubs only—implementation deferred to future features. |
| **KISS** | ✅ PASS | Architecture: (1) Approval extends existing workflow, (2) Mini App uses Telegram Web App API (standard platform), (3) Registration check via simple DB query, (4) UI uses CSS Grid (minimalistic layout). No complex state management or advanced patterns. |
| **DRY** | ✅ PASS | Reuses existing: SQLAlchemy models (AccessRequest renames ClientRequest), FastAPI patterns, python-telegram-bot handlers. Welcome message already sent via 001-request-approval webhook; audit trail in AccessRequest. No duplicate notification logic. |

### Technology Stack Compliance

| Component | Required | Compliant | Note |
|-----------|----------|-----------|------|
| **Backend Language** | Python 3.11+ | ✅ YES | Consistent with 001-request-approval |
| **HTTP Framework** | FastAPI | ✅ YES | Async-first, required for Mini App serving |
| **ORM** | SQLAlchemy + Alembic | ✅ YES | Extends existing schema, migrations included |
| **Database** | SQLite (dev) | ✅ YES | Per constitution |
| **Package Manager** | `uv` | ✅ YES | All dependencies via uv, `uv.lock` committed |
| **Testing Framework** | pytest | ✅ YES | Contract + integration tests required |
| **Telegram Library** | python-telegram-bot | ✅ YES | Required for bot integration |
| **Frontend** | HTML/CSS/JS (Telegram Web App API) | ✅ YES | No separate frontend infrastructure |
| **Secrets** | Environment variables only | ✅ YES | Telegram token, admin IDs via .env |

### Security Requirements Compliance

| Requirement | Status | Implementation |
|-------------|--------|-----------------|
| **No Hard-Coded Secrets** | ✅ PASS | Telegram bot token, admin IDs loaded from environment variables (use python-dotenv) |
| **Environment Variables** | ✅ PASS | Production deployment uses environment variables; local dev uses .env (not committed) |
| **No requirements.txt** | ✅ PASS | All dependencies managed via `uv` and `uv.lock` |

### Dependency Management

| New Dependency | Justification | MCP Context7 Required |
|---|---|---|
| None new (building on existing stack) | Reuses FastAPI, python-telegram-bot, SQLAlchemy from 001-request-approval | N/A for this phase; defer to implementation |

**Gate Result**: ✅ **PASS - No violations. Feature design complies with all constitution principles and standards.**

## Project Structure

### Documentation (this feature)

```text
specs/002-welcome-mini-app/
├── plan.md              # This file (implementation planning)
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings (UPDATED)
├── data-model.md        # Phase 1 data model (REFACTORED)
├── quickstart.md        # Phase 1 quickstart guide (UPDATED)
├── contracts/           # Phase 1 API contracts (UPDATED)
│   ├── mini-app-api.md  # Mini App backend API specification
│   └── (other contracts as needed)
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 implementation tasks (TBD - created by /speckit.tasks)
```

### Source Code Structure (existing + additions - Refactored)

```text
src/
├── api/
│   ├── __init__.py
│   ├── webhook.py          # Existing: Telegram webhook
│   └── mini_app.py         # NEW: Mini App endpoints (init, verify-registration, menu-action)
├── bot/
│   ├── __init__.py
│   ├── config.py           # Existing: Bot configuration
│   └── handlers.py         # Existing: Message handlers (includes approval response from 001)
├── models/
│   ├── __init__.py
│   ├── user.py             # REFACTORED: Unified User (is_client, is_administrator, is_owner, is_staff flags)
│   └── access_request.py   # REFACTORED: Renamed from client_request.py
├── services/
│   ├── __init__.py
│   ├── user_service.py     # NEW: User queries (is_approved check, etc.)
│   └── notification_service.py # Existing: Message delivery (already used for 001)
├── static/
│   └── mini_app/           # NEW: Mini App HTML/CSS/JS files
│       ├── index.html
│       ├── styles.css
│       └── app.js
└── main.py                 # Existing: FastAPI app entry point

migrations/
├── env.py
├── script.py.mako
└── versions/
    └── [timestamp]_refactor_user_model_and_add_mini_app_schema.py # Unified user with boolean roles

tests/
├── contract/
│   └── test_mini_app_endpoints.py          # NEW
├── integration/
│   ├── test_approval_flow.py               # Existing (uses new User model)
│   └── test_mini_app_flow.py               # NEW
└── unit/
    └── test_user_service.py                # NEW
```

**Structure Decision**: Single Python backend serves both Telegram bot (existing) and Mini App (new). No frontend project. HTML/CSS/JS in `src/static/mini_app/`. Maintains YAGNI/KISS alignment.

**YAGNI Application**: 
- No ApprovalNotification table (welcome already sent via 001-request-approval webhook)
- User model uses boolean flags (not single role enum) to allow multiple simultaneous roles
- MiniAppSession optional (can be added later if analytics needed)

## Complexity Tracking

> **Status**: ✅ No violations—YAGNI/KISS principles maintained. Fill section below only if violations arise during design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (None) | N/A | N/A |

**Justification**: Feature scope is tightly bounded (approval notification + registration check + menu display). Mini App frontend is intentionally minimal (no state management frameworks, no build pipeline, plain HTML/CSS/JS). Backend reuses existing architecture (FastAPI, SQLAlchemy, python-telegram-bot). No scaffolding for future features—menu items are navigation stubs only.
