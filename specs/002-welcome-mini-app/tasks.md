---

description: "Implementation tasks for 002-welcome-mini-app organized by user story"
---

# Tasks: Welcome Mini App for Approved Users

Input: Design documents from `/specs/002-welcome-mini-app/`
Prerequisites: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

Organization: Tasks are grouped by user story to enable independent implementation and testing of each story.

Format: `[ID] [P?] [Story] Description`
- [P]: Can run in parallel (different files, no dependencies)
- [Story]: User story label (US1, US2, US3)
- Include exact file paths in descriptions


## Phase 1: Setup (Shared Infrastructure)

Purpose: Ensure local environment and configuration for Mini App feature

- [X] T001 Create `.env.example` with Mini App variables at repo root (`/Users/serpo/Work/SOSenki/.env.example`) including TELEGRAM_MINI_APP_ID and MINI_APP_URL
- [X] T002 Add Mini App config constants in `src/bot/config.py` (read MINI_APP_URL, TELEGRAM_MINI_APP_ID from env)
- [X] T003 [P] Verify FastAPI app exposes health at `GET /health` in `src/main.py` (ensure ready for new routes)

---

## Phase 2: Foundational (Blocking Prerequisites)

Purpose: Core schema and service layer required by all stories

- [X] T004 Create unified `User` model with boolean role flags in `src/models/user.py`
- [X] T005 Refactor `ClientRequest` → `AccessRequest` model in `src/models/access_request.py` (rename from `src/models/client_request.py`)
- [X] T006 Create Alembic migration `[timestamp]_refactor_user_model_and_add_mini_app_schema.py` in `src/migrations/versions/` per `data-model.md`
- [X] T007 Update references from `client_request` to `access_request` in `src/services/request_service.py` (or create `access_request_service.py` if needed)
- [X] T008 [P] Implement `UserService` with `can_access_mini_app(telegram_id: str)` in `src/services/user_service.py`
- [X] T009 [P] Wire SQLAlchemy models into `src/models/__init__.py` for imports
- [X] T010 Mount static files under `/mini-app` in `src/main.py` using `src/static/mini_app/` directory
- [X] T011 Create static directory structure `src/static/mini_app/` (empty placeholders): `index.html`, `styles.css`, `app.js`
- [X] T012 [P] Create API router module `src/api/mini_app.py` (register APIRouter, no endpoints yet)
- [X] T013 Ensure test environment uses SQLite URL from env in `src/main.py` or app factory

Checkpoint: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Welcome message with App link (Priority: P1) 🎯 MVP

Goal: After admin approval, the user receives a Welcome message with a button to open the Mini App.

Independent Test: Approve a user → within 5 seconds user receives message containing an "Open App" button that launches the Mini App inside Telegram.

### Tests for User Story 1 (Contract/Integration)

- [X] T014 [P] [US1] Add integration test for approval → welcome with WebApp button in `tests/integration/test_approval_flow_to_mini_app.py`

### Implementation for User Story 1

- [X] T015 [US1] Add WebApp button to welcome notification in `src/services/notification_service.py` using `InlineKeyboardButton(web_app=WebAppInfo(url=MINI_APP_URL))`
- [X] T016 [US1] Ensure approval handler triggers updated notification in `src/bot/handlers.py` (after approval state change)
- [X] T017 [US1] Add MINI_APP_URL to config and inject into services in `src/bot/config.py`
- [X] T018 [US1] Manual sanity route to serve Mini App shell at `GET /mini-app` in `src/main.py` (opens `src/static/mini_app/index.html`)

Checkpoint: US1 complete — approved users receive a welcome with working Mini App button

---

## Phase 4: User Story 2 — Registered user sees Welcome + Menu (Priority: P1)

Goal: Registered (approved) users opening the Mini App see a welcome message and a main menu with Rule, Pay, Invest.

Independent Test: Open Mini App as an approved user → welcome content + three interactive menu items appear; design minimalistic with pine/water/sand colors.

### Tests for User Story 2 (Contract/Integration)

- [X] T019 [P] [US2] Contract test for `GET /api/mini-app/init` in `tests/contract/test_mini_app_endpoints.py`
- [X] T020 [P] [US2] Integration test for registered user Mini App load in `tests/integration/test_mini_app_flow.py`

### Implementation for User Story 2

- [X] T021 [P] [US2] Implement Telegram signature verification helper in `src/services/user_service.py` (or `src/services/mini_app_service.py`)
- [X] T022 [US2] Implement `GET /api/mini-app/init` in `src/api/mini_app.py` (returns registered status + menu for approved users)
- [X] T023 [P] [US2] Implement Mini App HTML shell in `src/static/mini_app/index.html` (welcome section + 3-item menu)
- [X] T024 [P] [US2] Implement nature-inspired styles in `src/static/mini_app/styles.css` (pine, water, sand palette via CSS variables)
- [X] T025 [P] [US2] Implement client logic in `src/static/mini_app/app.js` (WebApp init, call `/api/mini-app/init`, render registered view)
- [X] T026 [US2] Add basic error handling UI for network/signature errors in `src/static/mini_app/app.js`

Checkpoint: US2 complete — approved users see welcome + menu inside Mini App

---

## Phase 5: User Story 3 — Non-registered user sees Access Limited (Priority: P2)

Goal: Non-registered users are shown "Access is limited" with instructions to send `/request`.

Independent Test: Open Mini App as a non-registered user → access limited message displayed; no menu available; instruction text visible.

### Tests for User Story 3 (Contract/Integration)

- [X] T027 [P] [US3] Contract test for non-registered response from `GET /api/mini-app/init` in `tests/contract/test_mini_app_endpoints.py`
- [X] T028 [P] [US3] Integration test for non-registered Mini App load in `tests/integration/test_mini_app_flow.py`

### Implementation for User Story 3

- [X] T029 [US3] Ensure `/api/mini-app/init` returns `{ isRegistered: false, message, instruction }` for inactive users in `src/api/mini_app.py`
- [X] T030 [US3] Render access-limited state in `src/static/mini_app/app.js` (hide menu, show instruction to send `/request`)

Checkpoint: US3 complete — non-registered users receive access guidance

---

## Phase N: Polish & Cross-Cutting Concerns

Purpose: Quality, resilience, and developer experience improvements

- [X] T031 [P] Add `/api/mini-app/verify-registration` endpoint in `src/api/mini_app.py` (explicit refresh)
- [X] T032 [P] Add `/api/mini-app/menu-action` placeholder endpoint in `src/api/mini_app.py`
- [ ] T033 Implement rate limiting headers per contract in `src/api/mini_app.py`
- [ ] T034 [P] Add usage docs in `specs/002-welcome-mini-app/quickstart.md` (validate Mini App manual test steps)
- [ ] T035 Add graceful error response format and requestId in `src/api/mini_app.py`
- [ ] T036 [P] Update `alembic.ini` or env to ensure DB URL correctness for all environments
- [X] T037 Add unit tests for `UserService` in `tests/unit/test_user_service.py`
- [X] T038 Code cleanup: remove deprecated references to `client_request` and old role models in `src/services/`, `src/models/`, and `src/api/`

---

## Dependencies & Execution Order

Phase Dependencies
- Setup (Phase 1): No dependencies
- Foundational (Phase 2): Depends on Setup completion — BLOCKS all stories
- User Stories (Phase 3+): Depend on Foundational completion; US1 and US2 can proceed in parallel after Phase 2 (if desired), but MVP = US1 only
- Polish: After targeted stories

User Story Dependencies
- US1 (P1): No dependency on US2/US3; depends on Foundational
- US2 (P1): Depends on Foundational; independent of US1 logic, but UI link from US1 should open Mini App
- US3 (P2): Depends on Foundational; independent of US1; shares endpoint with US2

Within Each User Story
- Tests (if included) should be written first and fail before implementation
- Models → Services → Endpoints → Frontend wiring
- Ensure each story is independently testable

Parallel Opportunities
- [P] markers indicate safe parallelization: config, services, static UI files, and tests touching different files
- After Phase 2 completes, US1, US2 tasks marked [P] can be executed concurrently

---

## Parallel Example: User Story 2

Launch in parallel:
- Task: "Contract test for GET /api/mini-app/init in tests/contract/test_mini_app_endpoints.py" (T019)
- Task: "Implement Mini App HTML shell in src/static/mini_app/index.html" (T023)
- Task: "Implement client logic in src/static/mini_app/app.js" (T025)

---

## Parallel Example: User Story 1

Launch in parallel:
- Task: "Integration test for approval → welcome with WebApp button in tests/integration/test_approval_flow_to_mini_app.py" (T014)
- Task: "Add MINI_APP_URL to config in src/bot/config.py" (T017)

---

## Parallel Example: User Story 3

Launch in parallel:
- Task: "Contract test for non-registered response in tests/contract/test_mini_app_endpoints.py" (T027)
- Task: "Render access-limited state in src/static/mini_app/app.js" (T030)

---

## Implementation Strategy

MVP First (User Story 1 Only)
1. Complete Phase 1 and Phase 2
2. Implement US1 (T014–T018)
3. Validate: approve a user and verify welcome message includes working Mini App button

Incremental Delivery
1. Add US2 (T019–T026) → validate registered user menu
2. Add US3 (T027–T030) → validate access-limited state
3. Polish tasks as needed

