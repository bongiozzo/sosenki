# Contract: Makefile Seed Command Interface

**Version**: 1.0 | **Date**: November 10, 2025  
**Type**: End-to-end CLI contract | **Scope**: `make seed` command execution

## Command Specification

### Signature

```bash
make seed
```

### Exit Codes

| Code | Meaning | When | Recovery |
|------|---------|------|----------|
| 0 | SUCCESS | Database fully seeded, all tables populated | Done |
| 1 | FAILURE | Unable to complete; database state unchanged | Fix error, rerun |

### Output Format

**Destination**: stdout + `logs/seed.log`  
**Level**: INFO (progress feedback), WARN (skipped rows), ERROR (failures)  
**Format**: `[TIMESTAMP] [LEVEL] message`

Example successful run:
```
[2025-11-10 14:32:01] INFO Starting database seed...
[2025-11-10 14:32:02] INFO Loaded credentials from .vscode/google_credentials.json
[2025-11-10 14:32:03] INFO Fetched 65 rows from Google Sheet "Дома"
[2025-11-10 14:32:04] INFO Parsed 20 unique owners (users)
[2025-11-10 14:32:04] INFO Truncated existing data (users, properties)
[2025-11-10 14:32:05] INFO Inserted 20 users
[2025-11-10 14:32:05] INFO Inserted 65 properties
[2025-11-10 14:32:06] INFO ✓ Seed completed successfully
[2025-11-10 14:32:06] INFO Summary:
[2025-11-10 14:32:06] INFO   Users created: 20
[2025-11-10 14:32:06] INFO   Properties created: 65
[2025-11-10 14:32:06] INFO   Rows skipped: 0
[2025-11-10 14:32:06] INFO   Duration: 5.2 seconds
```

Example run with warnings:
```
[2025-11-10 14:32:01] INFO Starting database seed...
[2025-11-10 14:32:03] INFO Fetched 66 rows from Google Sheet "Дома"
[2025-11-10 14:32:04] WARN Row 45: Empty owner name (Фамилия), skipping property
[2025-11-10 14:32:04] WARN Row 52: Invalid decimal format "2,5ab" in Коэффициент, skipping property
[2025-11-10 14:32:04] INFO Parsed 20 unique owners (users)
[2025-11-10 14:32:04] INFO Inserted 20 users
[2025-11-10 14:32:05] INFO Inserted 64 properties (2 skipped)
[2025-11-10 14:32:06] INFO Summary:
[2025-11-10 14:32:06] INFO   Users created: 20
[2025-11-10 14:32:06] INFO   Properties created: 64
[2025-11-10 14:32:06] INFO   Rows skipped: 2
[2025-11-10 14:32:06] INFO   Duration: 5.1 seconds
```

Example error:
```
[2025-11-10 14:32:01] INFO Starting database seed...
[2025-11-10 14:32:03] INFO Fetched 65 rows from Google Sheet "Дома"
[2025-11-10 14:32:03] ERROR Credentials file not found: .vscode/google_credentials.json
[2025-11-10 14:32:03] ERROR Seed failed; database state unchanged
```

## Preconditions (Required Before Execution)

| Precondition | Status | Impact if Missing |
|--------------|--------|-------------------|
| `.env` file with `GOOGLE_SHEET_ID` and `GOOGLE_CREDENTIALS_PATH` configured | ✅ Required | ERROR, exit 1 |
| Credentials file at path configured via `GOOGLE_CREDENTIALS_PATH` env var exists | ✅ Required | ERROR, exit 1 |
| Application is offline (no active database connections) | ✅ Required | (documented; not enforced) |
| Python 3.11+ environment active | ✅ Required | ERROR, exit 1 |
| SQLite database initialized (schema exists) | ✅ Required | ERROR, exit 1 |
| Makefile seed target exists | ✅ Required | Make error, exit 2 |

## Postconditions (Guaranteed After Successful Exit)

| Postcondition | Guarantee | Verification |
|---------------|-----------|--------------|
| `users` table contains all unique owners from sheet | 100% | `SELECT COUNT(*) FROM users` = unique owner count |
| `properties` table contains all valid records from sheet | 100% | `SELECT COUNT(*) FROM properties` = total rows - skipped |
| Every `property.owner_id` references valid `users.id` | 100% | No FK constraint violations |
| All users have `is_investor=True`, `is_owner=True` | 100% | `SELECT COUNT(*) FROM users WHERE is_investor AND is_owner` = total users |
| User `is_administrator=True` only for owner name "Поляков" | 100% | Query: `SELECT name FROM users WHERE is_administrator` = ["Поляков"] (if present) |
| User `is_stakeholder` determined from "Доля в Терра-М" column | 100% | Validate against sheet data |
| Property `is_ready=True` when "Готовность" column = "Да" | 100% | Sample check against sheet |
| Property `is_for_tenant=True` when "Аренда" column = "Да" | 100% | Sample check against sheet |
| Database state is idempotent | 100% | Run seed twice consecutively; same result both times |
| `logs/seed.log` file created with full execution transcript | 100% | File exists, contains all log lines |

## Error Handling

### Error Case 1: Credentials File Not Found

**Trigger**: File specified in .env (or default) doesn't exist  
**Exit Code**: 1  
**Output**: `ERROR Credentials file not found: [filename]`  
**DB State**: UNCHANGED (error occurs before any DB operations)  
**User Action**: Create credentials file or update .env, rerun

### Error Case 2: Invalid Credentials (Auth Failure)

**Trigger**: Credentials file exists but JWT/service account auth fails  
**Exit Code**: 1  
**Output**: `ERROR Google Sheets API authentication failed: [reason]`  
**DB State**: UNCHANGED (error occurs before any DB operations)  
**User Action**: Verify credentials JSON format, rerun

### Error Case 3: Google Sheets API Unavailable

**Trigger**: Network error, timeout, or API rate limit  
**Exit Code**: 1  
**Output**: `ERROR Google Sheets API request failed: [reason]`  
**DB State**: UNCHANGED (error occurs before any DB operations)  
**Retry Policy**: NO AUTOMATIC RETRY (user must rerun manually)  
**Justification** (research.md): Simplicity over robustness

### Error Case 4: Empty Owner Name in Row

**Trigger**: "Фамилия" column is empty or whitespace-only  
**Exit Code**: 0 (partial success)  
**Output**: `WARN Row [N]: Empty owner name, skipping property`  
**DB State**: PARTIAL (other rows inserted normally)  
**Count**: Included in "Rows skipped" summary
**Justification** (spec.md Q2): Partial seed better than complete failure

### Error Case 5: Invalid Decimal Format

**Trigger**: "Коэффициент" or "Цена" can't be parsed as Russian decimal  
**Exit Code**: 0 (partial success)  
**Output**: `WARN Row [N]: Invalid decimal format "[value]" in [column], skipping property`  
**DB State**: PARTIAL (other rows inserted normally)  
**Count**: Included in "Rows skipped" summary
**Justification** (research.md): Skip on validation error

### Error Case 6: Owner Name Collision (Name Already Exists)

**Trigger**: Seeding second time without truncate (edge case)  
**Exit Code**: 1  
**Output**: `ERROR Duplicate user name "[name]"; cannot seed`  
**DB State**: ROLLBACK (transaction aborted)  
**Prevention**: Truncate-and-load pattern (see Phase 1 design)
**Note**: Truncate happens before insert, so this shouldn't occur in normal operation

### Error Case 7: Database Connection Failure

**Trigger**: SQLite database unavailable or corrupted  
**Exit Code**: 1  
**Output**: `ERROR Database connection failed: [reason]`  
**DB State**: UNCHANGED (error occurs before any transactions)  
**User Action**: Verify database file exists and is readable, rerun

## Test Contract Specification

### Contract Test (End-to-End)

**File**: `tests/contract/test_seeding_end_to_end.py`  
**Approach**: Mock Google Sheets API; use in-memory SQLite

```python
def test_seed_creates_users_and_properties():
    """Verify make seed command produces expected database state."""
    # Setup: Mock API, empty DB
    # Execute: make seed
    # Assert: users table has 20 rows, properties table has 65 rows
    # Assert: FK constraints satisfied
    # Assert: Exit code = 0

def test_seed_idempotent():
    """Verify running seed twice produces identical result."""
    # Execute: make seed (first time)
    result1 = get_db_checksum()
    # Execute: make seed (second time)
    result2 = get_db_checksum()
    # Assert: result1 == result2

def test_seed_handles_empty_owner_name():
    """Verify seed skips rows with empty owner name."""
    # Mock API: Include row with empty "Фамилия"
    # Execute: make seed
    # Assert: Row skipped (count in summary)
    # Assert: Log line contains "WARN...Empty owner name"
    # Assert: Exit code = 0 (partial success)

def test_seed_handles_invalid_decimal():
    """Verify seed skips rows with invalid decimals."""
    # Mock API: Include row with "abc" in Коэффициент
    # Execute: make seed
    # Assert: Row skipped
    # Assert: Log line contains "WARN...Invalid decimal"
    # Assert: Exit code = 0

def test_seed_assigns_correct_roles():
    """Verify user role flags assigned per spec."""
    # Execute: make seed
    # Query: SELECT name, is_administrator, is_stakeholder FROM users
    # Assert: is_investor=True for all
    # Assert: is_owner=True for all
    # Assert: is_administrator=True only for "Поляков"
    # Assert: is_stakeholder=True iff row has "Доля в Терра-М" value

def test_seed_fails_on_missing_credentials():
    """Verify clear error when credentials missing."""
    # Remove credentials file
    # Execute: make seed
    # Assert: Exit code = 1
    # Assert: Log contains "ERROR...Credentials file not found"
    # Assert: DB unchanged (no tables cleared)

def test_seed_fails_on_api_error():
    """Verify clear error when API unavailable."""
    # Mock API: Return error response
    # Execute: make seed
    # Assert: Exit code = 1
    # Assert: Log contains "ERROR...API request failed"
    # Assert: DB unchanged (no truncate occurred)
```

## Implementation Checklist

**Before merging, verify**:

- [ ] `make seed` command exists and is discoverable
- [ ] Exit codes 0 and 1 returned correctly
- [ ] Logs written to both stdout and `logs/seed.log`
- [ ] All preconditions validated with clear error messages
- [ ] All postconditions guaranteed after success
- [ ] Error handling matches spec (skip on validation, fail on API)
- [ ] Summary statistics accurate and logged
- [ ] Idempotency verified (seed twice = same result)
- [ ] All contract tests pass
- [ ] Performance <30 seconds for 65 properties

## References

- **Specification**: [spec.md](../spec.md)
- **Plan**: [plan.md](../plan.md)
- **Data Model**: [data-model.md](../data-model.md)
- **Research**: [research.md](../research.md)
