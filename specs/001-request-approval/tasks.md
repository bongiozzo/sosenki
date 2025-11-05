# Tasks: Client Request Approval Workflow

**Feature**: Client Request Approval Workflow (001-request-approval)  
**Input**: Design documents from `/specs/001-request-approval/`  
**Date**: 2025-11-04  
**Tech Stack**: Python 3.11+, FastAPI, SQLAlchemy, Alembic, SQLite, python-telegram-bot  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Test Strategy**: Contract tests first (define API behavior), then integration tests (full workflows), then unit tests (service logic). All tests are REQUIRED per feature specification (section: Development Workflow - Test-first approach).

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [TaskID] [P?] [Story?] Description (file path)`

- **[TaskID]**: Sequential number (T001, T002, etc.)
- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story (US1, US2, US3) - REQUIRED for user story phase tasks only
- **File path**: Exact location where task is completed

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and initialize core dependencies

**Status**: All tasks must complete before Phase 2 begins

- [X] T001 Create project structure per implementation plan in `src/` and `tests/`
- [X] T002 [P] Initialize `pyproject.toml` with dependencies: `python-telegram-bot[all]`, `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pytest`, `pytest-asyncio`, `pytest-mock`, `pydantic` in project root
- [X] T003 [P] Configure environment variables template in `.env.example` with TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, DATABASE_URL, WEBHOOK_URL, DEBUG
- [X] T004 Initialize uv lock file with `uv sync` and verify installation succeeds
- [X] T005 [P] Configure pytest settings in `pyproject.toml` with asyncio mode and test discovery patterns
- [X] T006 [P] Setup code linting configuration (ruff, type checking) in `pyproject.toml` per project standards

**Checkpoint**: Project structure ready, dependencies installed, environment configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Goal**: Establish database layer, Telegram bot infrastructure, FastAPI webhook structure, and shared services

**Independent Test Criteria**:

- Database migrations can be applied successfully
- Administrator config can be loaded from environment
- FastAPI server starts and webhook endpoint responds to requests
- Bot application is initialized and can dispatch updates to handlers

### Database & Migrations Infrastructure

- [X] T007 Create Alembic migration environment in `src/migrations/` with `alembic init` (if not exists)
- [X] T008 Configure Alembic `env.py` to use SQLAlchemy engine and target SQLite database URL from environment
- [X] T009 Create base SQLAlchemy model class in `src/models/__init__.py` with common fields (id, created_at, updated_at)

### Data Models (Base Entities)

- [X] T010 [P] Implement `ClientRequest` ORM model in `src/models/client_request.py` with fields: id, client_telegram_id, request_message, status, submitted_at, admin_telegram_id, admin_response, responded_at, created_at, updated_at; include unique constraint on (client_telegram_id, status='pending')
- [X] T011 [P] Implement `Administrator` ORM model in `src/models/admin_config.py` with fields: telegram_id (PK), name, active, created_at, updated_at
- [X] T012 Create initial Alembic migration in `src/migrations/versions/` to create ClientRequest and Administrator tables with all constraints and indexes

### Telegram Bot Infrastructure

- [X] T013 [P] Create bot configuration module in `src/bot/config.py` to load TELEGRAM_BOT_TOKEN and ADMIN_TELEGRAM_ID from environment; include validation
- [X] T014 Create bot application factory in `src/bot/__init__.py` that initializes `Application` from python-telegram-bot v20+ with async handlers support
- [X] T015 [P] Create handler registry pattern in `src/bot/handlers.py` (empty file with comments for handler functions: handle_request_command, handle_admin_approve, handle_admin_reject)

### FastAPI Webhook Setup

- [X] T016 Create FastAPI application factory in `src/api/webhook.py` with POST endpoint `/webhook/telegram` that accepts `Update` object and returns `{"ok": True}` (wire to bot application later)
- [X] T017 [P] Create main application entry point in `src/main.py` that initializes FastAPI app, bot application, and database connection; supports `--polling` and `--webhook` modes

### Shared Services

- [X] T018 [P] Create `NotificationService` skeleton in `src/services/notification_service.py` with async method `send_message(chat_id: str, text: str)` (delegates to bot.send_message)
- [X] T019 [P] Create `RequestService` skeleton in `src/services/request_service.py` with async methods: `create_request()`, `get_pending_request()`, `update_request_status()`, `get_request_by_id()`
- [X] T020 [P] Create `AdminService` skeleton in `src/services/admin_service.py` with async methods: `approve_request()`, `reject_request()`, `get_admin_config()`

### Database Setup

- [X] T021 Apply initial migration: `uv run alembic upgrade head` to create tables
- [X] T022 Create database connection pool in `src/services/__init__.py` (SQLAlchemy Session factory, Alembic context)

### Contract Tests (Framework Only)

- [X] T023 [P] Create contract test file `tests/contract/test_request_endpoint.py` with fixture for FastAPI TestClient; add placeholder test structure
- [X] T024 [P] Create contract test file `tests/contract/test_admin_handlers.py` with fixture for admin reply parsing; add placeholder test structure

**Checkpoint**: Foundation complete - database ready, bot infrastructure initialized, FastAPI webhook structure defined, shared services stubbed. Can now implement user stories in parallel.

---

## Phase 3: User Story 1 - Client Submits Access Request (Priority: P1) 🎯 MVP

**Goal**: Enable clients to submit access requests via `/request` command and receive confirmation. Requests are stored and made available to administrators.

**Independent Test Criteria**:

1. Client can send `/request` command with message
2. Request is stored in database with correct client_telegram_id, message content, timestamp, and status=pending
3. Client receives confirmation message within 2 seconds
4. Administrator is notified of request within 3 seconds (no user story 2 required for this test)
5. Duplicate pending requests are rejected with error message

### Contract Tests for User Story 1

> **NOTE: Write and RUN these tests FIRST - they MUST FAIL before implementation**

- [X] T025 [P] [US1] Contract test for `/request` command endpoint in `tests/contract/test_request_endpoint.py`: POST /webhook/telegram with /request update → returns 200, bot queues confirmation and admin notification
- [X] T026 [P] [US1] Contract test for duplicate request rejection in `tests/contract/test_request_endpoint.py`: POST /webhook/telegram with /request from client with existing PENDING request → returns 200, client receives error message "You already have a pending request"
- [X] T027 [US1] Integration test for full request submission flow in `tests/integration/test_client_request_flow.py`: client sends /request → database stores request → client receives confirmation → admin receives notification (all within timing SLAs)

### Implementation for User Story 1

- [X] T028 [P] [US1] Implement `create_request()` in `src/services/request_service.py`: accept client_telegram_id and request_message, validate no pending request exists, insert ClientRequest record with status=pending, return created request object
- [X] T029 [P] [US1] Implement `send_confirmation_to_client()` in `src/services/notification_service.py`: send message "Your request has been received and is pending review." to client Telegram ID
- [X] T030 [P] [US1] Implement `send_notification_to_admin()` in `src/services/notification_service.py`: send message with request details (including clickable client profile link), and inline keyboard with [Approve] [Reject] callback buttons to admin Telegram ID; buttons trigger admin handlers with request ID extracted from callback_data
- [X] T031 [US1] Implement `/request` command handler in `src/bot/handlers.py`: parse incoming Update object, extract client_id and message text, call request_service.create_request(), send confirmation via notification_service, send admin notification via notification_service, handle errors (duplicate request, DB error) and return appropriate messages to client
- [X] T032 [US1] Wire handler to bot application in `src/bot/__init__.py`: register handle_request_command with `/request` command filter
- [X] T033 [US1] Wire webhook endpoint to bot in `src/api/webhook.py`: POST /webhook/telegram endpoint calls application.process_update(update) to dispatch to handlers
- [X] T034 [P] [US1] Add logging to request submission flow in `src/bot/handlers.py` and `src/services/request_service.py`: log request creation, client confirmation sent, admin notification sent, errors
- [X] T035 [US1] Add error handling and validation in `/request` handler: validate message is not empty, validate client_telegram_id is present, catch and log database errors, return graceful error messages

**Checkpoint**: User Story 1 fully implemented and testable independently. Clients can submit requests, requests are stored, confirmations sent.

---

## Phase 4: User Story 2 - Administrator Reviews and Approves Request (Priority: P1)

**Goal**: Enable administrators to receive request notifications and approve requests. Upon approval, system grants client access and sends welcome message.

**Independent Test Criteria**:

1. Administrator receives notification with request details and reply buttons
2. Administrator can reply with "Approve" to request notification
3. Client receives welcome message within 5 seconds of admin approval
4. Request status transitions from pending → approved in database
5. Client account is marked as active/approved in system

### Contract Tests for User Story 2

> **NOTE: Write and RUN these tests FIRST - they MUST FAIL before implementation**

- [X] T036 [P] [US2] Contract test for admin approval handler in `tests/contract/test_admin_handlers.py`: POST /webhook/telegram with "Approve" reply from admin → returns 200, request status updated to approved, client receives welcome message
- [X] T037 [P] [US2] Contract test for approval with invalid request in `tests/contract/test_admin_handlers.py`: POST /webhook/telegram with "Approve" when request doesn't exist → returns 200, admin receives error "Request not found"
- [X] T038 [US2] Integration test for full approval flow in `tests/integration/test_approval_flow.py`: admin replies "Approve" to request notification → database updates request status → client receives welcome message with access granted message (within 5 second SLA)

### Implementation for User Story 2

- [X] T039 [P] [US2] Implement `get_pending_request()` in `src/services/request_service.py`: accept client_telegram_id, query database for request with status=pending, return request or None
- [X] T040 [P] [US2] Implement `update_request_status()` in `src/services/request_service.py`: accept request_id, new_status (approved/rejected), admin_response text, update database record with status, admin_telegram_id, admin_response, responded_at timestamp
- [X] T041 [P] [US2] Implement `send_welcome_message()` in `src/services/notification_service.py`: send message "Welcome to SOSenki! Your request has been approved and access has been granted. You can now use all features." to client Telegram ID
- [X] T042 [P] [US2] Implement `mark_client_active()` in `src/services/admin_service.py` OR extend ClientRequest model to track approval: update client record to active=true, or set approval flag in database
- [X] T043 [US2] Implement admin approval handler in `src/bot/handlers.py`: parse Update object with reply_to_message, extract original request details, validate "Approve" text (case-insensitive), call admin_service.approve_request() which updates status and sends welcome message, send confirmation to admin, handle errors (request not found, DB error)
- [X] T044 [US2] Wire approval handler to bot application in `src/bot/__init__.py`: register handle_admin_approve with filters for admin chat_id and "Approve" text match
- [X] T045 [P] [US2] Add logging to approval flow in `src/bot/handlers.py` and `src/services/admin_service.py`: log approval received, status update, welcome message sent, errors
- [X] T046 [US2] Add error handling in approval handler: validate admin is authorized, validate request exists, validate message is "Approve" format, catch database errors

**Checkpoint**: User Story 2 fully implemented. Administrators can approve requests, clients receive welcome messages, status transitions recorded. Stories 1 and 2 can now be tested together.

---

## Phase 5: User Story 3 - Administrator Rejects Request (Priority: P2)

**Goal**: Enable administrators to reject requests. Upon rejection, system notifies client with rejection message and no access is granted.

**Independent Test Criteria**:

1. Administrator can reply with "Reject" to request notification
2. Client receives rejection message within 5 seconds of admin rejection
3. Request status transitions from pending → rejected in database
4. Client account is NOT marked as active/approved
5. System prevents client from accessing SOSenki features

### Contract Tests for User Story 3

> **NOTE: Write and RUN these tests FIRST - they MUST FAIL before implementation**

- [X] T047 [P] [US3] Contract test for admin rejection handler in `tests/contract/test_admin_handlers.py`: POST /webhook/telegram with "Reject" reply from admin → returns 200, request status updated to rejected, client receives rejection message
- [X] T048 [P] [US3] Contract test for rejection with invalid request in `tests/contract/test_admin_handlers.py`: POST /webhook/telegram with "Reject" when request doesn't exist → returns 200, admin receives error "Request not found"
- [X] T049 [US3] Integration test for full rejection flow in `tests/integration/test_rejection_flow.py`: admin replies "Reject" to request notification → database updates request status → client receives rejection message (within 5 second SLA)

### Implementation for User Story 3

- [X] T050 [P] [US3] Implement `send_rejection_message()` in `src/services/notification_service.py`: send message "Your request for access to SOSenki has not been approved at this time. Please contact support if you have questions." to client Telegram ID
- [X] T051 [US3] Implement admin rejection handler in `src/bot/handlers.py`: parse Update object with reply_to_message, extract original request details, validate "Reject" text (case-insensitive), call admin_service.reject_request() which updates status and sends rejection message, send confirmation to admin, handle errors (request not found, DB error)
- [X] T052 [US3] Wire rejection handler to bot application in `src/bot/__init__.py`: register handle_admin_reject with filters for admin chat_id and "Reject" text match
- [X] T053 [P] [US3] Add logging to rejection flow in `src/bot/handlers.py` and `src/services/admin_service.py`: log rejection received, status update, rejection message sent, errors
- [X] T054 [US3] Add error handling in rejection handler: validate admin is authorized, validate request exists, validate message is "Reject" format, catch database errors

**Checkpoint**: User Story 3 fully implemented. All three user stories now work independently and together. Feature is MVP-complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple stories, documentation, testing completeness, and production readiness

### Documentation & Setup Validation

- [X] T055 [P] Validate and update `quickstart.md`: ensure all commands execute successfully, test scenarios match implementation, troubleshooting section covers all error cases
- [X] T056 [P] Create `DEPLOYMENT.md` documentation: cover production webhook setup, environment variables for production, database migration steps, monitoring/logging recommendations
- [X] T057 [P] Create `ARCHITECTURE.md` documentation: explain webhook flow, handler dispatcher pattern, service layer design, database schema, API contract

### Unit Tests (Service Layer)

- [X] T058 [P] Unit tests for `RequestService` in `tests/unit/test_request_service_simple.py`: test create_request (valid case, duplicate pending case), get_pending_request, update_request_status with all status transitions
- [X] T059 [P] Unit tests for `NotificationService` in `tests/unit/test_notification_service_simple.py`: test send_message, send_confirmation_to_client, send_notification_to_admin, send_welcome_message, send_rejection_message (all with mocked bot)
- [X] T060 [P] Unit tests for `AdminService` in `tests/unit/test_admin_service_simple.py`: test approve_request, reject_request, get_admin_config with various scenarios

### Integration Tests (Full Workflows)

- [X] T061 [P] Extend integration test for edge case: client submits request, doesn't receive immediate response, admin receives notification, time passes, admin still can approve (tests idempotency)
- [X] T062 [P] Extend integration test for concurrent requests: multiple clients submit requests simultaneously, all are recorded correctly with no duplicates, admin receives all notifications
- [X] T063 [P] Integration test for database persistence: create request, restart bot, verify request still exists with same data

### Error Handling & Logging

- [X] T064 [P] Add structured logging format in `src/main.py`: include timestamp, log level, component, message, request_id (if applicable) for all operations
- [X] T065 [P] Add error recovery: implement retry logic for transient failures (network, bot API timeouts), log all error states, graceful degradation
- [X] T066 [P] Add monitoring hooks: log metrics for request submission rate, admin response time, error rates, system health checks

### Code Quality & Performance

- [X] T067 [P] Run ruff linter and fix all issues: `uv run ruff check src/ tests/` with zero warnings
- [X] T068 [P] Run type checking: `uv run mypy src/` (if mypy configured) or use type hints throughout codebase
- [X] T069 [P] Performance optimization: verify request processing completes within SLAs (client confirm <2s, admin notify <3s, approval/rejection <5s); profile critical paths if needed
- [X] T070 [P] Code cleanup: remove dead code, consolidate duplicate logic, add docstrings to all public functions

### Final Validation

- [X] T071 Run full test suite: `uv run pytest -v tests/` → all tests pass (contract, integration, unit)
- [X] T072 Run quickstart guide end-to-end: follow `quickstart.md` from setup through approval flow, verify all steps succeed
- [X] T073 Code review checkpoint: review all implementation against spec.md requirements, verify no scope creep, confirm all success criteria met
- [X] T074 [P] Create `CONTRIBUTING.md` for future feature extensions: document code patterns, testing patterns, deployment process

**Checkpoint**: Feature complete, well-tested, documented, and production-ready. All user stories MVP-complete with comprehensive test coverage.

---

## Dependencies & Execution Strategy

### Phase Dependencies

```text
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← GATE: Must complete before user stories
    ↓
    ├─→ Phase 3 (US1 - Submit Request) ─→ Phase 4 (US2 - Approve) ─→ Phase 5 (US3 - Reject)
    │   (can run sequential or parallel if staffed)
    │
    └─→ Phase 6 (Polish & Cross-Cutting) ← Depends on all stories being complete
```

### Critical Path (Sequential, Single Developer)

1. **Phase 1**: Setup (6 tasks) - ~2 hours
2. **Phase 2**: Foundational (18 tasks) - ~6 hours
3. **Phase 3**: User Story 1 (11 tasks) - ~6 hours
4. **Phase 4**: User Story 2 (9 tasks) - ~5 hours
5. **Phase 5**: User Story 3 (8 tasks) - ~4 hours
6. **Phase 6**: Polish (20 tasks) - ~8 hours
**Total**: ~31 hours for complete MVP with comprehensive testing

### Parallel Opportunities (If Team Available)

- **Phase 1**: Tasks T002, T003, T005, T006 can run in parallel (2 hours total instead of sequential)
- **Phase 2**: Tasks T010, T011 (models) and T013, T014, T015 (bot) and T018, T019, T020 (services) can run in parallel
- **Phase 3, 4, 5**: Once Phase 2 complete:
  - If 3 developers: Each implements one user story in parallel (3 stories × 5-6 hours each = 5-6 hours total instead of 15 hours)
  - If 2 developers: US1 + US2 first (11 hours), then US3 (4 hours)
  - If 1 developer: Sequential critical path above

### Parallel Example: Phase 3 (User Story 1) - If Team Capacity

**3 developers working in parallel on different files**:

```bash
# Developer A: Tests
uv run pytest tests/contract/test_request_endpoint.py -v    # T025, T026
uv run pytest tests/integration/test_client_request_flow.py -v  # T027

# Developer B: Services
# Implement T028 request_service.create_request()
# Implement T029, T030 notification_service methods
# Implement T034 logging

# Developer C: Handlers & Wiring
# Implement T031 /request command handler
# Implement T032 handler registration
# Implement T033 webhook wiring
# Implement T035 error handling

# Integration: Once all three complete and tests pass (T027), merge and verify
```

### Suggested MVP Scope & Phasing for Release

**MVP Release 1 (Phase 1-3)**: Basic request submission

- Deliver Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (User Story 1)
- Value: Clients can submit requests, administrators notified
- Estimate: ~14 hours

**MVP Release 2 (Phase 4)**: Approval workflow

- Deliver Phase 4 (User Story 2)
- Value: Administrators can approve and clients get welcome message
- Estimate: +5 hours (total ~19 hours)

**MVP Release 3 (Phase 5)**: Rejection workflow

- Deliver Phase 5 (User Story 3)
- Value: Administrators can reject requests, full approval control
- Estimate: +4 hours (total ~23 hours)

**Production Release (Phase 6)**: Polish & hardening

- Deliver Phase 6 (Polish, comprehensive testing, documentation)
- Value: Production-ready, well-tested, documented
- Estimate: +8 hours (total ~31 hours)

### Task Execution Checklist

For each task:

1. ✅ Read task description and understand file path
2. ✅ If task is a TEST: Write test FIRST, verify it FAILS (red phase)
3. ✅ Implement feature/code to make test PASS (green phase)
4. ✅ Refactor for clarity (refactor phase)
5. ✅ Run full test suite: `uv run pytest -v tests/`
6. ✅ Check linting: `uv run ruff check .`
7. ✅ Mark task complete and move to next
8. ✅ At each checkpoint, verify all tasks in that phase pass

---

## Task Statistics

- **Total Tasks**: 74
- **Setup Phase**: 6 tasks
- **Foundational Phase**: 18 tasks
- **User Story 1 (Request Submission)**: 11 tasks
- **User Story 2 (Approval)**: 9 tasks
- **User Story 3 (Rejection)**: 8 tasks
- **Polish & Cross-Cutting**: 22 tasks
- **Parallelizable Tasks**: 38 tasks marked with [P]
- **Sequential Dependencies**: 36 tasks requiring previous completion

**Test Coverage**:

- Contract Tests: 7 tasks (define API behavior first)
- Integration Tests: 6 tasks (verify full workflows)
- Unit Tests: 3 tasks (verify service logic)
- **Total Test Tasks**: 16 tasks (~20% of all tasks)

---

## Success Criteria

Upon completion of all 74 tasks:

✅ All three user stories fully implemented and independently testable  
✅ 100% of acceptance criteria from spec.md satisfied  
✅ All contract tests passing (API contract validated)  
✅ All integration tests passing (full workflows validated)  
✅ All unit tests passing (service logic validated)  
✅ Code passes linting and type checks  
✅ Request processing meets all SLAs (request <2s, notification <3s, response <5s)  
✅ Database schema correctly implements data-model.md  
✅ Comprehensive documentation (quickstart, architecture, deployment, contributing)  
✅ Production-ready with monitoring, logging, error handling  
✅ Feature ready for release to production

---

## References

- **Specification**: `/specs/001-request-approval/spec.md`
- **Implementation Plan**: `/specs/001-request-approval/plan.md`
- **Data Model**: `/specs/001-request-approval/data-model.md`
- **API Contracts**: `/specs/001-request-approval/contracts/`
- **Research**: `/specs/001-request-approval/research.md`
- **Quickstart Guide**: `/specs/001-request-approval/quickstart.md`
- **Project Constitution**: `/PROJECT_CONSTITUTION.md`
