# Implementation Plan: Client Request Approval Workflow

**Branch**: `001-request-approval` | **Date**: 2025-11-04 | **Spec**: [Feature Specification](spec.md)
**Input**: Feature specification from `/specs/001-request-approval/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a Telegram bot workflow enabling new SOSenki clients to request access by sending `/request` command. The bot forwards requests to a predefined administrator, who can approve (triggering welcome message and access grant) or reject (triggering rejection message). The system persists all requests for audit purposes and prevents duplicate pending requests from the same client.

**Core Value**: Enables frictionless client onboarding through Telegram (the platform our users already use), with administrative gatekeeping to control access.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `python-telegram-bot` library (async webhooks), FastAPI (request handling), SQLAlchemy (ORM), Alembic (migrations)  
**Storage**: SQLite (development); production database per deployment context  
**Testing**: pytest (unit + integration), contract tests via curl/requests library  
**Target Platform**: Linux server (Telegram webhook receiver)  
**Project Type**: Single backend service with Telegram Bot frontend  
**Performance Goals**: Sub-second request/approval cycle; handle 100s of concurrent requests  
**Constraints**: Telegram API rate limits (30 messages/sec per bot); request processing MUST complete within 5 seconds per spec  
**Scale/Scope**: MVP handles 10-100s of requests/day; future versions may add bulk operations or filtering

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Alignment

✅ **YAGNI (You Aren't Gonna Need It)**

- Feature strictly implements 3 user stories only (request submission, approval, rejection)
- No bulk operations, expiration logic, filtering, or appeal workflows (explicitly out of scope)
- Simple message-based responses (not complex forms or state machines)
- **Status**: PASS - No speculative features

✅ **KISS (Keep It Simple, Stupid)**

- Telegram API integration (already familiar, well-documented)
- SQLAlchemy ORM (standard, straightforward for simple tables)
- FastAPI webhook receiver (minimal, clean routing)
- Stateless request handlers (no complex state machines)
- **Status**: PASS - Simplest viable architecture chosen

✅ **DRY (Don't Repeat Yourself)**

- Shared request storage entity (ClientRequest) used by all flows
- Admin/client message handlers reuse core notification service
- Database migrations centralized via Alembic
- **Status**: PASS - No duplication

### Technology Stack Compliance

✅ **Backend Stack**

- Python 3.11+ ✓
- FastAPI ✓ (webhook endpoint)
- SQLAlchemy + Alembic ✓ (request persistence)
- SQLite ✓ (default)
- `python-telegram-bot` ✓ (Telegram integration)

✅ **Dependency Management**

- pyproject.toml (single source) ✓
- uv.lock (reproducible) ✓
- No requirements.txt ✓
- MCP Context7 will be used for library best practices ✓

✅ **Security Requirements**

- No hard-coded secrets (admin Telegram ID via env var) ✓
- Environment variables for bot token ✓
- .env for local dev only ✓

✅ **Development Workflow**

- Test-first approach (contract tests before handlers) ✓
- TDD red-green-refactor cycle ✓
- Contract + integration tests required ✓

**GATE RESULT**: ✅ **PASS** - Feature fully compliant with constitution. No complexity exceptions needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-request-approval/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (research findings)
├── data-model.md        # Phase 1 output (entity models)
├── quickstart.md        # Phase 1 output (dev setup guide)
├── contracts/           # Phase 1 output (API specs)
│   ├── request_endpoint.yaml
│   └── handler_contracts.md
├── checklists/
│   └── requirements.md   # Quality checklist
└── tasks.md             # Phase 2 output (task breakdown)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── __init__.py
│   ├── client_request.py    # ClientRequest ORM model
│   ├── admin_config.py      # Administrator configuration
│   └── client.py            # Client profile (future expansion)
├── services/
│   ├── __init__.py
│   ├── request_service.py   # ClientRequest business logic
│   ├── notification_service.py  # Telegram message dispatch
│   └── admin_service.py     # Admin approval/rejection handling
├── bot/
│   ├── __init__.py
│   ├── handlers.py          # Telegram command handlers (/request, admin responses)
│   └── config.py            # Bot token, admin ID from environment
├── api/
│   ├── __init__.py
│   └── webhook.py           # FastAPI webhook endpoint for Telegram
├── migrations/              # Alembic migrations
│   └── versions/
└── main.py                  # Application entry point

tests/
├── contract/
│   ├── test_request_endpoint.py      # POST /webhook/telegram contract tests
│   └── test_admin_handlers.py        # Admin reply handler contract tests
├── integration/
│   ├── test_client_request_flow.py   # Full client request → admin notification
│   ├── test_approval_flow.py         # Admin approve → client welcome
│   └── test_rejection_flow.py        # Admin reject → client rejection message
├── unit/
│   ├── test_request_service.py
│   ├── test_notification_service.py
│   └── test_admin_service.py
└── conftest.py             # Shared fixtures (mock bot, database, etc.)

pyproject.toml             # Dependencies (python-telegram-bot, FastAPI, SQLAlchemy, pytest, etc.)
uv.lock                    # Locked dependencies
.env.example               # Environment variable template (bot token, admin ID, database URL)
```

**Structure Decision**: Single backend service (Option 1 variant). Telegram provides the UI (bot messages); we implement async webhook receiver + service layer. No separate frontend needed per architecture decision.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

**Status**: ✅ No complexity exceptions needed. Feature fully aligns with constitution and uses simplest viable architecture.

## Next Steps (Phase 0 - Research)

1. Research best practices for `python-telegram-bot` async webhooks (via MCP Context7)
2. Research FastAPI webhook integration patterns
3. Research SQLAlchemy + Alembic for simple request tracking
4. Research pytest fixtures for Telegram bot testing
5. Document findings in `research.md`

## Next Steps (Phase 1 - Design)

1. Generate `data-model.md` with ClientRequest, Administrator, Client entities and relationships
2. Generate API contracts in `contracts/` (webhook endpoint schema, message handlers)
3. Generate `quickstart.md` with local development setup (env vars, uv sync, running bot)
4. Run `update-agent-context.sh` to register new technologies with AI agent

---

**Ready for Phase 0 Research**: Yes
