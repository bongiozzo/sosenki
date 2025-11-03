# Tasks for 001-seamless-telegram-auth

Feature: Seamless Telegram Auth (branch: `001-seamless-telegram-auth`)

Notes:

- Follow test-first where noted by writing failing tests before implementation.
- Paths assume backend code under `backend/app/` and tests under `backend/tests/` per plan.

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 [P] Initialize Python project dependencies and dev tools (add FastAPI, pytest, python-telegram-bot) in `backend/pyproject.toml` (use `uv` and `uv.lock` to pin dependencies;)
- [x] T002 [P] Add project linting and formatting configs: `backend/pyproject.toml` (black) and `.flake8` at repo root
- [x] T003 [P] Create base FastAPI app entrypoint `backend/app/main.py` and ASGI startup scaffolding
- [x] T004 [P] Add env config helper `backend/app/config.py` and document required env vars in `.env.example`
- [x] T005 [P] Add database connection helper `backend/app/database.py` and register it in `backend/app/main.py`

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T006 Setup database migrations framework (Alembic) and add initial migration directory `backend/migrations/` (files and config)
- [x] T007 [P] Create base models module `backend/app/models/__init__.py` and a base `Base` SQLAlchemy metadata in `backend/app/models/base.py`
- [x] T008 [P] Add tests harness and folders: create `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/contract/` and `backend/tests/conftest.py`
- [x] T009 [P] Implement error handling and API response helpers in `backend/app/api/errors.py`
- [x] T010 [P] Add observability scaffolding (basic logging config) in `backend/app/logging.py`

## Phase 3: User Story 1 - Открытие Mini App и быстрая проверка пользователя (Priority: P1) 🎯 MVP

Goal: Verify initData, return linked status and, if unlinked, provide the frontend with a short request form payload.

Independent test: POST `/miniapp/auth` with `init_data` → returns `linked: true` + user object when SOSenkiUser exists, otherwise `linked: false` and `request_form` fields.

### Tests (US1 — Test-First)

- [x] T011 [P] [US1] Contract test for `POST /miniapp/auth` against `specs/001-seamless-telegram-auth/contracts/openapi.yaml` in `backend/tests/contract/test_miniapp_auth_contract.py`
- [x] T012 [US1] Unit test for initData signature & auth_date validation in `backend/tests/unit/test_initdata_validation.py` (should fail initially)

### Implementation (US1)

- [x] T013 [P] [US1] Create `TelegramUserCandidate` model in `backend/app/models/telegram_user_candidate.py`
- [x] T014 [P] [US1] Add `telegram_id` column to `backend/app/models/user.py` (existing SOSenkiUser model) with unique constraint and migration file in `backend/migrations/`
- [x] T015 [US1] Implement `backend/app/services/telegram_auth_service.py` with function `verify_initdata(init_data: dict) -> dict` (uses Telegram hash check and timestamp rule)
- [x] T016 [US1] Implement API route handler `backend/app/api/routes/miniapp.py` with `POST /miniapp/auth` that calls `telegram_auth_service.verify_initdata`, queries `SOSenkiUser` by `telegram_id`, and returns the contract-shaped response
- [x] T017 [US1] Add request validation schemas `backend/app/schemas/miniapp.py` (Pydantic) and wire into route
- [x] T018 [US1] Integration test for happy path `backend/tests/integration/test_miniapp_auth.py` (initData->existing user -> welcome) that initially fails
- [x] T019 [US1] Integration test for unlinked user `backend/tests/integration/test_miniapp_auth_unlinked.py` that initially fails

## Phase 4: User Story 2 - Отправка запроса на подключение (Priority: P2)

Goal: Allow an unlinked Telegram user to submit a short request; deduplicate by `telegram_id` and create `TelegramUserCandidate` record.

Independent test: POST `/requests` as an unlinked user → 201 with `Request` object; duplicate requests are blocked.

### Tests (US2 — Test-First)

- [x] T020 [P] [US2] Contract test for `POST /requests` in `backend/tests/contract/test_requests_contract.py`
- [x] T021 [US2] Unit test for deduplication logic in `backend/tests/unit/test_request_dedup.py` (should fail initially)

### Implementation (US2)

- [x] T022 [P] [US2] Implement request create route `backend/app/api/routes/requests.py` with `POST /requests`
- [x] T023 [US2] Implement `backend/app/services/request_service.py` to encapsulate creation/dedup logic (raise `DuplicateRequestError` if duplicate)
- [x] T024 [US2] Add Pydantic schemas `backend/app/schemas/requests.py`
- [x] T025 [US2] Integration test for create-request flow `backend/tests/integration/test_create_request_flow.py` (create -> DB record present -> admin notified queue)
- [x] T026 [US2] Implement notification enqueue in `backend/app/services/telegram_bot.py` (function to send message to Admin Group Chat); provide an in-memory/mock transport for tests

## Phase 5: User Story 3 - Обработка запроса администратором (Priority: P3)

Goal: Admins can list pending requests and perform accept/reject actions; on accept create a SOSenkiUser with role and handle duplicate `telegram_id` as `user_already_exists`.

Independent test: Admin accepts a request → new SOSenkiUser created with `telegram_id` and role; user receives notification.

### Tests (US3 — Test-First)

- [x] T027 [P] [US3] Contract test for `POST /admin/requests/{request_id}/action` in `backend/tests/contract/test_admin_action_contract.py`
- [x] T028 [US3] Unit test for AdminAction audit creation in `backend/tests/unit/test_admin_action_audit.py` (should fail initially)
- [x] T029 [US3] Integration test for accept flow `backend/tests/integration/test_admin_accept_flow.py` covering create-on-accept and duplicate handling

### Implementation (US3)

- [x] T030 [P] [US3] Implement admin endpoints in `backend/app/api/routes/admin_requests.py` (`GET /admin/requests`, `POST /admin/requests/{request_id}/action`)
- [x] T031 [US3] Implement `backend/app/services/admin_service.py` that verifies admin user role, performs accept/reject, creates `SOSenkiUser` on accept, creates `AdminAction` audit record
- [x] T032 [US3] Add migration to create `admin_action` table `backend/migrations/XXXX_admin_action.py`
- [x] T033 [US3] Implement notification send to Telegram user on accept/reject in `backend/app/services/telegram_bot.py` (use mock in tests)
- [x] T034 [US3] Add HTTP error mapping for `user_already_exists` with 400 response and machine-friendly error code in `backend/app/api/errors.py`

## Phase X: Polish & Cross-Cutting Concerns

- [x] T035 [P] Add contract test runner to CI configured to run `backend/tests/contract/` and fail on regressions
- [x] T036 [P] Add integration tests to CI stage and ensure DB migrations run in CI job
- [x] T037 [P] Add docs updates: `specs/001-seamless-telegram-auth/SEAMLESS-TELEGRAM-AUTH.md` summarizing how to run the feature locally
- [x] T038 [P] Security review: ensure initData verification and secrets handling documented in `backend/SECURITY.md`

---

## Dependencies & Execution Order

- Setup (Phase 1) tasks T001..T005 can run immediately and in parallel
- Foundational (Phase 2) tasks T006..T010 must complete before any user story tasks start
- User stories (Phase 3/4/5) require foundational phase complete; within each story tests should be written first

### Story mapping / task counts

- US1 tasks: T011..T019 (9 tasks)
- US2 tasks: T020..T026 (7 tasks)
- US3 tasks: T027..T034 (8 tasks)
- Setup + Foundational + Polish: T001..T010 and T035..T038 (14 tasks)

Total tasks: 38

### Parallel opportunities

- Many setup/foundation tasks marked `[P]` can proceed in parallel (deps: different files)
- Contract tests (T011, T020, T027) can be implemented in parallel with their unit tests
- Models across stories are parallelizable when they don't share files

### Implementation strategy (recommended)

1. Complete Phase 1 and Phase 2 (T001..T010) to provide consistent scaffolding and migrations
2. Run contract tests for US1 (T011) and unit tests for initData (T012) — get failing tests in place
3. Implement US1 (T013..T019) until tests pass; verify independently
4. Repeat for US2 then US3
5. Add CI hooks for contract and integration tests (T035..T036)

---

## Files created

- `specs/001-seamless-telegram-auth/tasks.md` (this file)
