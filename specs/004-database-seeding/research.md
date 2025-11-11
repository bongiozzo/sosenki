# Research: Database Seeding from Google Sheets

**Date**: November 10, 2025  
**Feature**: 004-database-seeding  
**Phase**: 0 - Outline & Research

## Research Questions & Findings

### 1. Google Sheets API Integration

**Question**: What is the recommended approach for authenticating to Google Sheets API from a Python development tool?

**Decision**: Use service account authentication with `google-auth` library and JSON credentials file.

**Rationale**: 
- Service accounts are designed for server-to-server interactions (no user interaction required)
- JSON keyfile method aligns with environment variable-based credential configuration
- `google-auth` is the official, well-maintained library from Google
- Avoids OAuth2 complexity unnecessary for a development tool

**Alternatives Considered**:
- OAuth2 user authentication: Requires user consent flow; unnecessary complexity for internal dev tool
- API key authentication: Less secure for accessing private sheets; requires explicit API key in config
- Shared credentials file: Fragile; easier to get out of sync

**Implementation Details**:
- Use `google.auth.service_account` to load credentials from JSON file
- Construct `google.oauth2.service_account.Credentials` with appropriate scopes: `https://www.googleapis.com/auth/spreadsheets.readonly`
- Use `google-api-python-client` library's `sheets()` resource to fetch data

---

### 2. Data Type Parsing Strategy for Russian Formatting

**Question**: How should we parse Russian number formatting (decimal commas, thousand separators)?

**Decision**: Implement format-aware parsing with explicit handling for each data type.

**Rationale**:
- Russian locale uses comma as decimal separator and space as thousand separator
- Google Sheets API returns "UNFORMATTED_VALUE" (raw numbers) alongside "FORMATTED_VALUE" (locale-specific text)
- Using UNFORMATTED_VALUE directly is most reliable approach

**Parsing Strategy**:
- For share weights (percentages like "3,85%"): 
  - Fetch FORMATTED_VALUE, strip "%" suffix
  - Replace comma with period for Decimal conversion
  - Example: "3,85%" → 3.85 → Decimal("3.85")
  
- For prices (currency like "р.7 000 000,00"):
  - Fetch FORMATTED_VALUE, strip "р." prefix and spaces
  - Replace comma with period
  - Example: "р.7 000 000,00" → 7000000.00 → Decimal("7000000.00")
  
- For booleans ("Да"/"Нет"):
  - Simple string matching: "Да" → True, everything else (including empty) → False

**Alternative Considered**:
- Use `locale.atof()`: Requires locale configuration; more fragile across different environments
- Regex extraction: Works but less readable than explicit string operations

---

### 3. Idempotency & Transaction Handling

**Question**: How should we ensure idempotency without complex transaction management?

**Decision**: Implement truncate-and-load pattern with database transactions for atomicity.

**Rationale**:
- Truncate ensures clean state; no stale records can remain
- Load within single transaction provides atomicity: all-or-nothing semantics
- Prevents partial seeding if failure occurs mid-load
- No complex locking needed (spec clarification: seed runs offline)

**Implementation**:
- Wrap all operations in SQLAlchemy session/transaction
- `session.execute(delete(User))`  and `session.execute(delete(Property))` to truncate
- Load new records within same transaction
- `session.commit()` after all loads succeed; `session.rollback()` if error occurs

**Alternative Considered**:
- Diff-and-merge (only update changed records): Complex comparison logic; doesn't guarantee clean state
- Soft deletes with date-based filtering: Complicates queries; doesn't align with development use case

---

### 4. Owner Name Uniqueness & User Lookup

**Question**: Should User.name be strictly unique, and how should we handle name collisions?

**Decision**: User.name is unique constraint (per User model); collision handling: prefer exact match, log warning if ambiguous.

**Rationale**:
- User.name is already defined as unique in user.py model
- Google Sheet contains one row per property; owner names are identifiers
- Likelihood of exact collision in current data set: very low (all names are distinct)
- Fail-fast approach (constraint violation) is cleaner than silent merge

**Lookup Algorithm**:
```
1. Query User by name (exact match)
2. If found: use that User's ID for Property.owner_id
3. If not found: create new User with role defaults (resolved in clarification)
4. If name is empty/whitespace: skip row, log WARNING (resolved in clarification)
```

**Alternative Considered**:
- Fuzzy matching (Levenshtein distance): Over-engineered; risks merging distinct owners
- Case-insensitive matching: Unnecessary complexity; names in sheet are consistent

---

### 5. Logging Configuration & Output

**Question**: How should the seeding process provide progress feedback?

**Decision**: Use Python `logging` module with INFO level; output to both stdout and file (logs/seed.log).

**Rationale**:
- `logging` is standard Python library; no external dependency
- INFO level provides visibility without excessive verbosity
- Dual output (stdout + file) gives real-time feedback to developer and audit trail for debugging
- WARN/ERROR messages highlighted naturally by terminal colors

**Logging Structure**:
- Logger name: `sostenki.seeding.main` (follows module hierarchy)
- Handlers:
  - `StreamHandler(sys.stdout)` with INFO level
  - `FileHandler("logs/seed.log")` with INFO level, ISO format timestamps
- Example log lines:
  ```
  [2025-11-10 14:23:45] INFO Starting database seed from Google Sheets...
  [2025-11-10 14:23:46] INFO Fetching 'Дома' sheet data (65 properties)...
  [2025-11-10 14:23:47] WARNING Skipping row 12: empty owner name
  [2025-11-10 14:23:48] INFO Created User: Иванчик/Радионов (is_investor=True, is_stakeholder=True)
  [2025-11-10 14:23:49] INFO Loaded 65 properties in 2.3 seconds
  [2025-11-10 14:23:49] INFO Database seed complete!
  ```

**Alternative Considered**:
- No logging, just return exit code: Difficult to debug failures
- Structured JSON logging: Overkill for development tool; reduces readability

---

### 6. Makefile Integration & Entrypoint Design

**Question**: What is the best way to expose the seeding function as a `make seed` command?

**Decision**: Create Python CLI module in `src/cli/seed.py` with entry point, expose via Makefile target.

**Rationale**:
- Makefile is standard development tool; developers expect `make seed` pattern
- Makefile delegates to Python script; separates build orchestration from implementation
- Allows future expansion to other Makefile targets without modifying Python code
- Aligns with existing project structure (src/api/, src/services/, etc.)

**Implementation**:
```makefile
.PHONY: seed
seed:
	@python -m src.cli.seed

.PHONY: help
help:
	@echo "make seed        - Refresh development database from Google Sheets"
```

**Alternative Considered**:
- Direct shell script: Less maintainable; duplicates logic if seeding used elsewhere
- Add to pyproject.toml scripts: Less discoverable; developers don't expect `uv run seed`

---

### 7. Configuration File Locations & Resolution

**Question**: Where should configuration files (credentials, Sheet ID) be located?

**Decision**: Use `.env` for Sheet ID and path to credentials; service account JSON as separate file in project root or via env var.

**Rationale**:
- `.env` is standard for development configuration; matches existing team patterns
- Service account JSON in project root and .env, both are .gitignored
- Alternative: ENV vars only, but explicit .env file aids discoverability

**Configuration Resolution**:
```python
- Alternative: ENV vars only, but explicit .env file aids discoverability

**Configuration Resolution**:
```python
# 1. Try load from environment variables
sheet_id = os.getenv("GOOGLE_SHEET_ID")
creds_file = os.getenv("GOOGLE_CREDENTIALS_PATH", ".vscode/google_credentials.json")

# 2. Fall back to .env file if not in environment
if not sheet_id:
    from dotenv import load_dotenv
    load_dotenv(".env")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
```

# 3. Fail with clear error if still missing
if not sheet_id or not os.path.exists(creds_file):
    raise ConfigurationError("...")
```

**Alternative Considered**:
- YAML config file: Overkill for 2 settings; .env more standard for development
- Hardcoded defaults: Violates security requirements; difficult to change

---

### 8. Error Handling & Graceful Degradation

**Question**: How should the system respond to API failures vs. data validation errors?

**Decision**: Fail fast on API/auth errors; skip individual rows on validation errors with warning.

**Rationale**:
- API failures (auth, rate limit, network) are environmental issues → fail immediately (no-retry per clarification)
- Data validation errors (empty name, invalid number) are data quality issues → skip row, log warning, continue
- Allows partial seed success while alerting to problems

**Error Categories**:
1. **Fatal Errors** (fail immediately):
   - Missing/invalid credentials file
   - Authentication failure
   - Google Sheets API unavailable
   - Database connection error

2. **Validation Errors** (skip row, log warning):
   - Empty/whitespace owner name
   - Invalid share weight format
   - Database constraint violation (duplicate property, orphaned FK)

3. **Recoverable Errors** (log and continue):
   - Duplicate row in sheet (update existing vs. skip)

**Implementation**:
```python
try:
    # Fetch from API
except (FileNotFoundError, PermissionError) as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)
except google.auth.exceptions.GoogleAuthError as e:
    logger.error(f"Authentication failed: {e}")
    sys.exit(1)

# For each row:
try:
    validate_and_create(row)
except ValueError as e:
    logger.warning(f"Skipping row {row_num}: {e}")
    skipped_count += 1
```

---

### 9. Testing Strategy

**Question**: What test coverage is needed for the seeding system?

**Decision**: Contract tests for end-to-end flow, integration tests for Google Sheets fetch + DB write, unit tests for parsers.

**Rationale**:
- Contract tests validate single `make seed` command produces expected database state
- Integration tests isolate API + database interactions (mock Google Sheets API)
- Unit tests verify data type parsing correctness

**Test Structure**:
```
tests/
├── contract/
│   └── test_seeding_end_to_end.py
│       - Given: fresh SQLite DB, mock Google Sheets API with known data
│       - When: run seed command
│       - Then: verify DB contains exact expected state (counts, values, relationships)
│       - Test idempotency: run twice, verify state unchanged
│       - Test skip behavior: run with empty owner names in sheet, verify count logged
│
├── integration/
│   └── test_google_sheets_integration.py
│       - Mock Google Sheets API responses
│       - Verify correct API calls (Sheet ID, range, fields)
│       - Verify credential loading
│       - Test error handling (API rate limit, network error)
│
└── unit/
    ├── test_data_type_parsing.py
    │   - Parse Russian percentages ("3,85%" → Decimal)
    │   - Parse Russian currency ("р.7 000 000,00" → Decimal)
    │   - Parse booleans ("Да"/"Нет" → True/False)
    │
    └── test_user_role_assignment.py
        - New user gets is_investor=True, is_owner=True
        - Поляков gets is_administrator=True
        - is_stakeholder based on "Доля в Терра-М"
```

---

## Summary of Decisions

| Area | Decision | Why |
|------|----------|-----|
| API Auth | Service account (JSON credentials) | Designed for server-to-server; no user interaction |
| Data Parsing | Format-aware (strip prefix/suffix, replace comma) | Reliable; handles Russian locale |
| Idempotency | Truncate-and-load within transaction | Simple; guarantees clean state |
| User Lookup | Exact name match; fail on ambiguity | User.name is unique; fail-fast is cleaner |
| Logging | INFO level to stdout + file | Real-time feedback + audit trail |
| Entrypoint | Python CLI via Makefile | Discoverable; extensible |
| Config | .env + env vars + JSON credentials file | Standard patterns; .gitignored |
| Error Handling | Fail fast on API errors; skip row on validation errors | Environmental vs. data quality issues |
| Testing | Contract + integration + unit | Comprehensive coverage of key flows |

---

## Phase 0 Complete

All "NEEDS CLARIFICATION" items from Technical Context have been resolved through research. System is ready for Phase 1: data model design and contract specification.
