# Architecture: Database Seeding from Google Sheets

**Version**: 1.0 | **Date**: November 10, 2025  
**Status**: ✅ Phases 1-3 Complete (Implementation & Testing Finished)  
**Current Phase**: Phase 4 (Polish & Review)

## System Overview

The database seeding system is a Python CLI tool integrated with the SOSenki project's Makefile. It synchronizes the local development SQLite database with canonical property and user data stored in a Google Sheet ("SosenkiPrivate" → "Дома" tab).

**Key Characteristic**: One-way, offline-only data load. The tool truncates existing data and replaces it with fresh data from the sheet in a single atomic transaction.

```
┌────────────────────────────────┐
│  SosenkiPrivate Google Sheet   │  (Source of Truth)
│  Sheet: "Дома" (65 properties) │
└────────────────┬───────────────┘
                 │
        Google Sheets API
        (Service Account Auth)
                 │
                 ▼
┌────────────────────────────────┐
│  Python CLI Tool               │
│  Entry: src/cli/seed.py        │
│  Exposed: make seed            │
└────────────────┬───────────────┘
                 │
                 │ (Parse, Validate, Transform)
                 │ - Russian decimal parsing
                 │ - User role assignment
                 │ - Owner lookup
                 │
                 ▼
┌────────────────────────────────┐
│  SQLite Development Database   │
│  Tables: users (20), properties (65)
│  Constraint: All FK valid      │
└────────────────────────────────┘
```

## Architecture Layers

### 1. **Presentation Layer** (CLI)

**File**: `src/cli/seed.py`  
**Interface**: Command-line entry point  
**Responsibilities**:
- Parse command-line arguments (if any)
- Load environment configuration (.env)
- Initialize logging (stdout + file)
- Call seeding service
- Return exit code (0 = success, 1 = failure)
- Handle uncaught exceptions with clear user messages

**Example Execution**:
```bash
make seed
# Calls: python -m src.cli.seed (or similar)
# Output: Logs to stdout + logs/seed.log
# Return: Exit code 0 or 1
```

### 2. **Orchestration Layer** (Seeding Service)

**File**: `src/services/seeding.py`  
**Responsibilities**:
- Coordinate entire seeding workflow
- Manage transaction lifecycle (begin, commit, rollback)
- Call Google Sheets fetcher, parsers, database operations
- Aggregate statistics (users created, properties created, rows skipped)
- Handle partial success (skip invalid rows, continue with valid ones)
- Return structured result (status, summary, errors)

**Flow**:
```python
def seed_database():
    session = create_session()
    try:
        # 1. Fetch data
        rows = google_sheets_client.fetch("Дома")
        
        # 2. Parse data
        users, properties, skipped = parse_all(rows)
        
        # 3. Atomic DB transaction
        with session.begin():
            session.query(Property).delete()
            session.query(User).delete()
            session.add_all(users)
            session.flush()
            session.add_all(properties)
            session.flush()
            validate_foreign_keys(session)
        
        # 4. Return summary
        return SeedResult(
            success=True,
            users_created=len(users),
            properties_created=len(properties),
            rows_skipped=len(skipped),
            errors=skipped
        )
    except (AuthError, APIError):
        session.rollback()
        return SeedResult(success=False, error=str(e))
```

### 3. **Data Access Layer** (Services)

#### 3a. Google Sheets Service

**File**: `src/services/google_sheets.py`  
**Responsibilities**:
- Authenticate with Google Sheets API (service account)
- Fetch sheet data (rows as dictionaries)
- Handle API errors with clear messages
- No retry logic (caller handles retry)

**Interface**:
```python
class GoogleSheetsClient:
    def __init__(self, credentials_path, sheet_id):
        # Load service account JSON
        # Authenticate with google-auth
        
    def fetch_sheet(self, sheet_name):
        # Return: List[Dict[str, Any]]
        # Keys: Column headers from sheet
        # Raises: AuthError, APIError
```

#### 3b. Parser Service

**File**: `src/services/parsers.py`  
**Responsibilities**:
- Convert raw sheet values to typed entity fields
- Handle Russian number formatting (comma decimals, space thousands separator)
- Apply business logic (role assignment, boolean conversion)
- Log warnings on validation errors; skip row on error

**Core Functions**:
```python
def parse_russian_decimal(value_str: str) -> Decimal:
    # "1 000,25" → Decimal('1000.25')
    # Raises: ValueError on invalid format

def parse_user_row(row: Dict) -> Optional[User]:
    # row = {"Фамилия": "Поляков", "Доля в Терра-М": "30%", ...}
    # Returns: User entity or None if skip
    # Logs: WARNING if row skipped

def parse_property_row(row: Dict, user_lookup: Dict[str, User]) -> Optional[Property]:
    # row = {"Дом": "Terrace 5", "Коэффициент": "0,5", ...}
    # Returns: Property entity or None if skip
    # Logs: WARNING if row skipped
```

#### 3c. Database Service (SQLAlchemy ORM)

**Integration**: Existing ORM (`src/models/user.py`, `src/models/property.py`)  
**Responsibilities**:
- Define User and Property entities
- Enforce schema constraints (PK, FK, UNIQUE)
- Manage session lifecycle
- Execute batch inserts (transaction atomicity)

### 4. **Configuration Layer**

**Sources**:
- `.env` file (GOOGLE_SHEET_ID, optional: LOG_LEVEL, CREDENTIALS_PATH)
- External JSON file (Google service account credentials)
- Makefile (seed target definition)

**Loading Order**:
1. .env file (primary)
2. Environment variables (override)
3. Defaults (fallback)

**Example .env**:
```
GOOGLE_SHEET_ID=your-google-sheet-id-here
GOOGLE_CREDENTIALS_PATH=.vscode/google_credentials.json
LOG_LEVEL=INFO
LOG_FILE=logs/seed.log
```

### 5. **Logging Layer**

**Handler 1: Console (stdout)**
- Level: INFO
- Format: `[TIMESTAMP] [LEVEL] message`
- Use: Real-time feedback during execution

**Handler 2: File (logs/seed.log)**
- Level: INFO
- Format: Same as console
- Use: Audit trail for troubleshooting

**Log Categories**:
- INFO: Progress updates (API fetch, row parse, DB insert, final summary)
- WARNING: Validation errors (empty owner, invalid decimal; row skipped)
- ERROR: Failure (missing credentials, API unavailable, FK violation)

## Error Handling Strategy

### Error Classification

**Fail-Fast Errors** (exit code 1, no DB changes):
- Missing credentials file
- Invalid credentials (auth failure)
- Google Sheets API unavailable
- Database connection error
- FK constraint violation on insert

**Skip-Row Errors** (exit code 0, partial DB changes):
- Empty owner name in "Фамилия" column
- Invalid decimal format in "Коэффициент" or "Цена"
- Any row-level validation failure

**Transaction-Level Guarantees**:
- Fail-fast errors: Transaction never started (no table truncate)
- Skip-row errors: Transaction completes with valid rows (truncate + partial insert)
- Atomicity: Either all-or-nothing within transaction; no partial row inserts

### Error Handling Implementation

```python
def seed_database():
    session = create_session()
    try:
        # Fail-fast errors (before transaction)
        rows = google_sheets_client.fetch("Дома")  # May raise AuthError
        
        with session.begin():  # Transaction starts here
            session.query(Property).delete()
            session.query(User).delete()
            
            for row in rows:
                try:
                    user = parse_user_row(row)  # May skip
                    if user:
                        session.add(user)
                except ValueError:
                    log.warning(f"Row skipped: {row}")
                    continue
            
            session.flush()  # FK constraints checked here
            # If any FK error, exception raised, transaction rolls back
            
        return SUCCESS
        
    except (AuthError, APIError) as e:
        log.error(f"Fatal error: {e}")
        session.rollback()
        return FAIL
```

## Data Model Mapping

**User Entity** (from "Фамилия" column, unique):
- `name` ← "Фамилия" (owner name, unique constraint)
- `is_investor` ← True (always)
- `is_owner` ← True (always)
- `is_administrator` ← True if name == "Поляков", else False
- `is_stakeholder` ← True if "Доля в Терра-М" has value

**Property Entity** (one per row):
- `owner_id` ← User lookup by "Фамилия" name
- `property_name` ← "Дом"
- `type` ← "Размер"
- `share_weight` ← parse_russian_decimal("Коэффициент")
- `is_ready` ← "Готовность".lower() == "да"
- `is_for_tenant` ← "Аренда".lower() == "да"
- `photo_link` ← "Фото" (optional)
- `sale_price` ← parse_russian_decimal("Цена") (optional)

**See also**: [data-model.md](data-model.md) for complete field definitions and validation rules.

## Idempotency Design

**Pattern**: Truncate-and-load  
**Guarantee**: Running seed twice consecutively produces identical database state

**Implementation**:
1. DELETE all rows from properties table (preserves schema)
2. DELETE all rows from users table
3. INSERT all parsed users
4. INSERT all parsed properties
5. COMMIT (all-or-nothing)

**Result**: Previous state erased; new state replaces it. Running twice = no change on second run (same data inserted both times).

**Trade-off**: Simpler than diff-merge approach; acceptable for development tool use case.

## Performance Characteristics

**Target**: <30 seconds for 65 properties + 20 users

**Breakdown**:
- Google Sheets API fetch: ~2-3 seconds
- Data parsing (Russian decimals, role logic): ~1 second
- DB truncate + insert + commit: ~1-2 seconds
- Logging + summary: <1 second

**Scaling**: Linear with row count (no nested loops, single-pass parsing).

**Bottleneck**: Google Sheets API latency (network I/O). Database operations are fast (SQLite batch insert).

## Testing Strategy

### Contract Tests (End-to-End)

**File**: `tests/contract/test_seeding_end_to_end.py`  
**Approach**: Mock Google Sheets API; use real SQLite database (test instance)  
**Coverage**:
- Successful seed (all rows imported)
- Idempotency (seed twice = same result)
- Error handling (empty names, invalid decimals)
- Role assignment (is_administrator, is_stakeholder)
- Exit codes (0 = success, 1 = failure)

### Integration Tests (API + Database)

**File**: `tests/integration/test_seeding_flow.py`  
**Approach**: Mock Google Sheets API; integration with real database and logging  
**Coverage**:
- Full end-to-end workflow
- Transaction rollback on error
- Logging to file and stdout
- Concurrent database access handling

### Unit Tests (Components)

**File**: `tests/unit/test_parsers.py`  
**Coverage**: Russian decimal parsing, role assignment logic

**File**: `tests/unit/test_user_role_assignment.py`  
**Coverage**: is_administrator, is_stakeholder conditional logic

## Security Considerations

### Credentials Management

- **No hardcoding**: Service account JSON stored in external file (not in code)
- **No secrets in logs**: Credentials not logged; only successes/errors
- **.gitignore**: Credentials file excluded from git (path configured via GOOGLE_CREDENTIALS_PATH env variable)
- **Environment variables**: GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_PATH in .env (also .gitignored)

### Database Access

- **Service account**: Google Sheets API has minimal permissions (read-only on specific sheet)
- **Offline operation**: Seed requires app to be offline (prevents concurrent write conflicts)
- **Transaction isolation**: SQLite transactions prevent partial updates

### Logging Privacy

- Sheet data logged only for errors (user names, property counts OK to log)
- No sensitive data logged beyond what's in database

## Deployment Model

**Environment**: Local development only  
**Execution**: Manual (`make seed` command)  
**Frequency**: As-needed when database state requires reset  
**Rollback**: Previous state available via database backup (if needed)

**Not designed for**:
- Production use (would expose credentials)
- Scheduled/automated execution (data sync one-way only)
- Real-time sync (sheet updates don't auto-update DB)

## Future Extensions (Out of Scope - Phase 2+)

- Sync transaction tables (payments, allocations) from different sheets
- Bidirectional sync (update sheet from database)
- Incremental updates (upsert instead of truncate)
- Scheduled sync (cron job)
- Web UI for seed trigger + progress monitoring

## References

- **Specification**: [spec.md](spec.md)
- **Plan**: [plan.md](plan.md)
- **Data Model**: [data-model.md](data-model.md)
- **Contracts**: [contracts/makefile-interface.md](contracts/makefile-interface.md)
- **Quickstart**: [quickstart.md](quickstart.md)
- **Research**: [research.md](research.md)
- **Constitution**: [constitution.md](./.specify/memory/constitution.md)
