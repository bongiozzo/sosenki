# Implementation Plan: Database Seeding from Google Sheets

**Branch**: `004-database-seeding` | **Date**: November 10, 2025  
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary

Implement a developer-facing database seeding tool that synchronizes the local development database with canonical data from the SOSenkiPrivate Google Sheet. A single `make seed` command will fetch User and Property records from the "Дома" sheet via the Google Sheets API, parse Russian number formatting, maintain relational integrity, and log progress in real-time. The process is idempotent (truncate-and-load) and secure (credentials from external files).

**Key Goals**:
- Single unattended command execution
- 100% data accuracy and relational integrity
- Sub-30-second performance for current data volume
- Clear error messages and progress feedback

## Technical Context

**Language/Version**: Python 3.11+ (per constitution)  
**Primary Dependencies**: 
- `google-auth` + `google-api-python-client` (Google Sheets API)
- `sqlalchemy` (existing ORM)
- `alembic` (existing migrations)
- `python-dotenv` (config loading)

**Storage**: SQLite (development) via SQLAlchemy ORM  
**Testing**: pytest (contract/integration/unit)  
**Target Platform**: Local development (macOS/Linux with `make`)  
**Project Type**: Python backend CLI tool  
**Performance Goals**: Seed completes in <30 seconds for 65 properties + 20 users  
**Constraints**: Unattended execution; no database corruption on failure; offline-only operation (app must be stopped)  
**Scale/Scope**: Phase 1 MVP = User + Property from "Дома" sheet only; transaction tables deferred to Phase 2

## Constitution Check

✅ **GATE PASSED** - All constitution requirements satisfied:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **YAGNI - Database Schema** | ✅ Pass | Only User and Property entities (already in schema); no speculative tables added |
| **YAGNI - No future-proofing** | ✅ Pass | Implementation is minimal; only required fields mapped from sheet |
| **KISS - Simple approach** | ✅ Pass | Straightforward truncate-and-load pattern; no complex diff/merge logic |
| **DRY - Code reuse** | ✅ Pass | Data type parsing extracted to reusable utility module `src/services/parsers.py` |
| **Python 3.11+** | ✅ Pass | Target version specified; no deprecated APIs used |
| **SQLAlchemy + Alembic** | ✅ Pass | Existing ORM and migrations used as-is |
| **No hard-coded secrets** | ✅ Pass | Credentials loaded from .env and external JSON file |
| **uv for dependency management** | ✅ Pass | Dependencies managed via `pyproject.toml` + `uv.lock` (no requirements.txt) |
| **MCP Context7 documentation** | ✅ Pass | All new libraries documented via Context7 before implementation |

**Re-check after Phase 1**: Design review will verify no new entities or fields added beyond spec requirements.

## Implementation Phases

### Phase 0: Research (COMPLETE)

✅ Completed. See [research.md](research.md) for:
- Google Sheets API integration approach
- Russian data type parsing strategy
- Idempotency & transaction handling
- User lookup and role assignment logic
- Logging configuration
- Makefile integration
- Configuration file resolution
- Error handling strategy
- Testing approach

### Phase 1: Design & Contracts (THIS PHASE)

**Deliverables**:
1. `data-model.md` - Entity definitions and data flow
2. `contracts/` directory - API contracts (Makefile interface spec)
3. `quickstart.md` - Developer setup & execution guide
4. Agent context update

**Artifacts to Create**:

#### 1. Data Model (`data-model.md`)

**User Entity** (existing, used as-is):
- `id` (primary key)
- `name` (unique) - from "Фамилия" column
- `telegram_id` (nullable)
- `is_active` (default True)
- `is_investor` (default True for seeded users)
- `is_owner` (default True for seeded users)
- `is_administrator` (True only for owner name "Поляков")
- `is_stakeholder` (True if "Доля в Терра-М" column has value)
- `created_at`, `updated_at`

**Property Entity** (existing, used as-is):
- `id` (primary key)
- `owner_id` (foreign key → User.id)
- `property_name` - from "Дом" column
- `type` - from "Размер" column (Большой/Малый/etc.)
- `share_weight` (Decimal) - from "Коэффициент" column
- `is_active` (default True)
- `is_ready` (Boolean) - from "Готовность" column (Да=True, else=False)
- `is_for_tenant` (Boolean) - from "Аренда" column (Да=True, else=False)
- `photo_link` (nullable) - from "Фото" column
- `sale_price` (Decimal, nullable) - from "Цена" column

**Data Flow**:
```
Google Sheet "Дома"
    ↓
Google Sheets API (service account auth)
    ↓
Python data type parsers (Russian format handling)
    ↓
User lookup/creation (name matching + role defaults)
    ↓
Property creation (owner_id resolution)
    ↓
SQLAlchemy ORM (insert into SQLite)
    ↓
Transaction commit (all-or-nothing atomicity)
```

#### 2. Contracts (`contracts/`)

**Interface**: `make seed` command

**Contract Spec** (`contracts/makefile-interface.md`):
```
Command: make seed
Exit Code: 0 (success) or 1 (failure)
Output: INFO-level logs to stdout + logs/seed.log
Preconditions:
  - .env file with GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_PATH configured
  - credentials file (referenced via GOOGLE_CREDENTIALS_PATH env variable)
  - application is offline (no active database connections)
Postconditions (success):
  - users table contains all owners from sheet (with role defaults)
  - properties table contains all records from sheet (linked to users)
  - database state is identical to running seed twice immediately after
Error Cases:
  - Missing credentials file → exit 1, clear error message
  - Invalid credentials → exit 1, clear error message
  - Empty owner name → skip row, log WARNING, count in summary
  - API unavailable → exit 1, clear error message (no retry)
```

#### 3. Quickstart (`quickstart.md`)

Structure:
- Setup: Install dependencies, configure .env
- Usage: Run `make seed`
- Troubleshooting: Common errors and fixes
- Development: Testing the seeding locally
- Offline requirement: Document that app must be stopped

#### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh copilot` to update Copilot context with new technologies:
- `google-auth` library
- `google-api-python-client` library
- Data type parsing patterns
- Service account authentication flow

## Project Structure

### Documentation (this feature)

```text
specs/004-database-seeding/
├── spec.md              # Feature specification
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 entity definitions (to create)
├── quickstart.md        # Phase 1 developer guide (to create)
├── contracts/           # Phase 1 interface contracts (to create)
│   └── makefile-interface.md
└── tasks.md             # Phase 2 task breakdown (future: /speckit.tasks command)
```

### Source Code Structure

```text
src/
├── models/              # (existing: User, Property)
├── services/
│   ├── google_sheets.py (NEW) - API client and data fetching
│   ├── parsers.py       (NEW) - Russian data type parsing utilities
│   └── seeding.py       (NEW) - Orchestration: truncate/load/validate
├── cli/
│   └── seed.py          (NEW) - Entry point for `make seed` command
└── ...

tests/
├── contract/
│   └── test_seeding_end_to_end.py (NEW)
├── integration/
│   ├── test_google_sheets_api.py (NEW)
│   └── test_seeding_flow.py (NEW)
├── unit/
│   ├── test_parsers.py (NEW)
│   └── test_user_role_assignment.py (NEW)
└── ...

Makefile (existing - ADD seed target)
.env (existing - ADD GOOGLE_SHEET_ID if not present)
logs/ (NEW - directory for seed.log)
```

## Implementation Sequence

1. **Setup** (before Phase 2):
   - Create src/services/parsers.py with data type conversion functions
   - Create src/services/google_sheets.py with API client
   - Create src/services/seeding.py with orchestration logic
   - Create src/cli/seed.py entry point
   - Add `seed` target to Makefile
   - Create tests directory structure

2. **Core Logic** (Phase 2 tasks):
   - Implement data type parsers (test-first)
   - Implement Google Sheets API client (mock in tests)
   - Implement seeding orchestration (truncate, load, commit)
   - Implement CLI entry point
   - Implement error handling and logging

3. **Integration** (Phase 2 tasks):
   - Contract tests (end-to-end with mock API)
   - Integration tests (Google Sheets + Database)
   - Unit tests (parsers, role assignment)

4. **Documentation** (Phase 2):
   - Quickstart guide with setup steps
   - Troubleshooting section
   - Code comments for complex parsing logic

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Truncate-and-load (not diff-merge) | Simple, idempotent, guarantees clean state |
| Service account auth | Designed for server-to-server; no user interaction |
| No retry logic on API failure | Simplicity; transient failures require manual re-run |
| Skip rows with empty names (not fail) | Partial seed better than complete failure; issues logged |
| INFO logging to stdout + file | Real-time feedback + audit trail |
| Python CLI wrapped by Makefile | Discoverable; extensible for future targets |
| Role flags assigned on creation | Aligns with business logic from clarifications |
| is_stakeholder from "Доля в Терра-М" column | Transparent mapping from sheet data |

## Complexity Justification

✅ **NO CONSTITUTION VIOLATIONS** - All design choices align with YAGNI, KISS, and DRY principles. No speculative features or unnecessary complexity introduced.

## Next Steps

1. **Create Phase 1 artifacts** (this session):
   - data-model.md - complete entity and data flow documentation
   - quickstart.md - developer setup and usage guide
   - contracts/makefile-interface.md - execution contract specification

2. **Update agent context**:
   - Run update script to add Google Sheets libraries to Copilot context

3. **Proceed to Phase 2** (`/speckit.tasks` command):
   - Generate detailed task breakdown with estimates
   - Define acceptance criteria for each task
   - Sequence tasks for parallel development

## References

- **Specification**: [spec.md](spec.md)
- **Research**: [research.md](research.md)
- **Constitution**: [constitution.md](/.specify/memory/constitution.md)
- **Service Models**: [user.py](src/models/user.py), [property.py](src/models/property.py)

