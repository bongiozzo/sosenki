# Quickstart: Database Seeding

**Version**: 1.0 | **Date**: November 10, 2025  
**Time to Complete**: 5-10 minutes

## Overview

This guide walks you through setting up and running the database seeding tool, which synchronizes your local development database with data from the SOSenkiPrivate Google Sheet.

**What it does**: Fetches 20 users and 65 properties from Google Sheets → parses Russian number formats → inserts into SQLite database.  
**Time required**: ~5 seconds to run.  
**When to use**: After setting up the development environment, or when you need a fresh copy of canonical data.

## Prerequisites

- Python 3.11+ installed and active
- SOSenki project cloned locally
- Google service account credentials (JSON file)
- Google Sheet ID for SOSenkiPrivate

## Step 1: Obtain Google Credentials

1. **Option A: Use existing credentials file** (if already set up)
   - Check if credentials file exists at path configured in `GOOGLE_CREDENTIALS_PATH` env var
   - If yes, skip to Step 2

2. **Option B: Create new service account** (first time setup)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select a project
   - Enable Google Sheets API
   - Create a Service Account
   - Generate JSON key
   - Share SOSenkiPrivate Google Sheet with service account email
   - Download JSON key → save to location specified in `.env` GOOGLE_CREDENTIALS_PATH

**Security**: Never commit credentials file to git (already in .gitignore).

## Step 2: Configure Environment

1. **Open `.env` file** in project root
   ```bash
   cat .env
   ```

2. **Add or verify `GOOGLE_SHEET_ID` entry**:
   ```
   GOOGLE_SHEET_ID=your-google-sheet-id-here
   ```
   
   (The ID is the long alphanumeric string in the Google Sheet URL after `/d/`)

3. **Save file**

## Step 3: Install Dependencies

```bash
# From project root
cd path/to/SOSenki

# Install project dependencies (includes google-auth, google-api-python-client)
uv sync

# Verify installation
python -c "import google.auth; print('✓ google-auth installed')"
python -c "import googleapiclient; print('✓ google-api-python-client installed')"
```

## Step 4: Verify Database Exists

```bash
# Check if database file exists
ls -la src/db.sqlite

# If not, initialize schema
cd src && alembic upgrade head && cd ..
```

## Step 5: Run Seed Command

```bash
# From project root
make seed
```

**Expected output** (should complete in ~5 seconds):
```
[2025-11-10 14:32:01] INFO Starting database seed...
[2025-11-10 14:32:02] INFO Loaded credentials from .vscode/google_credentials.json
[2025-11-10 14:32:03] INFO Fetched 65 rows from Google Sheet "Дома"
[2025-11-10 14:32:04] INFO Parsed 20 unique owners (users)
[2025-11-10 14:32:04] INFO Inserted 20 users
[2025-11-10 14:32:05] INFO Inserted 65 properties
[2025-11-10 14:32:06] INFO ✓ Seed completed successfully
[2025-11-10 14:32:06] INFO Summary:
[2025-11-10 14:32:06] INFO   Users created: 20
[2025-11-10 14:32:06] INFO   Properties created: 65
[2025-11-10 14:32:06] INFO   Rows skipped: 0
[2025-11-10 14:32:06] INFO   Duration: 5.2 seconds
```

**Exit code**: 0 (check with `echo $?`)

## Step 6: Verify Data

```bash
# Check users were inserted
sqlite3 src/db.sqlite "SELECT COUNT(*) as user_count FROM users;"

# Should output: 20 (or similar)

# Check properties were inserted
sqlite3 src/db.sqlite "SELECT COUNT(*) as property_count FROM properties;"

# Should output: 65 (or similar)

# View sample data
sqlite3 src/db.sqlite "SELECT name, is_administrator, is_stakeholder FROM users LIMIT 5;"
```

## Step 7: Check Logs

```bash
# View seed execution log
cat logs/seed.log

# Follow log in real-time on next run
tail -f logs/seed.log &  # background
make seed                 # foreground
```

## Understanding the "Доп" Column (Auxiliary Properties)

The Google Sheet includes an optional "Доп" (Дополнительно - "Additional") column that specifies auxiliary property types. This column enables creating multiple property records for a single owner in the sheet row.

### "Доп" Column Format

If the "Доп" column contains a property type, an additional property record is created:

| Column | Main Property | Auxiliary Property |
|--------|---------------|-------------------|
| Фамилия (Owner) | Петров | Петров |
| Адрес (Address) | ул. Пушкина, д. 1 | - |
| Готовность (Ready) | Да | Да |
| **Доп** | *(empty)* | **Большой** |

**Result**: Owner "Петров" gets TWO property records:
1. Main: "ул. Пушкина, д. 1" (type: empty, share_weight: from sheet)
2. Auxiliary: unnamed (type: "Большой", share_weight: NULL, for_tenant: false)

### Supported "Доп" Types

```
- "Большой" (Large House)
- "Малый" (Small House)
- "Беседка" (Gazebo)
- "Хоздвор" (Farm Building)
- "Склад" (Warehouse)
- "Баня" (Bathhouse)
```

### Auxiliary Property Behavior

**Inherited from main property**:
- `owner_id` - Same owner
- `is_ready` - From "Готовность" column
- `is_for_tenant` - From sheet (typically false)

**Set to NULL/Default**:
- `share_weight` - NULL (auxiliary structures don't get allocation shares)
- `photo_link` - NULL
- `sale_price` - NULL

### Example Seeding Output

```
✓ Users created: 20
✓ Main properties created: 65
✓ Auxiliary properties created: 12 (from "Доп" column)
✓ Total properties: 77
✓ Execution time: 2.3s
```

## Troubleshooting

### Error: "Credentials file not found"

**Symptom**:
```
ERROR Credentials file not found: sosenkimcp-8b756c9d2720.json
```

**Fix**:
1. Download JSON key from Google Cloud Console
2. Set GOOGLE_CREDENTIALS_PATH in .env to point to the credentials file
3. Place credentials file at the path specified in .env
4. Verify: `ls -la $(grep GOOGLE_CREDENTIALS_PATH .env | cut -d= -f2)`
5. Rerun: `make seed`

### Error: "Authentication failed"

**Symptom**:
```
ERROR Google Sheets API authentication failed: Invalid credentials
```

**Fix**:
1. Verify JSON file is valid: `cat $(grep GOOGLE_CREDENTIALS_PATH .env | cut -d= -f2) | python -m json.tool`
2. Check service account email is shared on Google Sheet (Sheet → Share → add email)
3. Verify JSON file has `private_key` and `client_email` fields
4. Regenerate key if needed (see Step 1)
5. Rerun: `make seed`

### Error: "GOOGLE_SHEET_ID not found"

**Symptom**:
```
ERROR GOOGLE_SHEET_ID not configured in .env
```

**Fix**:
1. Open `.env` file
2. Add: `GOOGLE_SHEET_ID=your-google-sheet-id-here`
3. Save file
4. Rerun: `make seed`

### Error: "Database connection failed"

**Symptom**:
```
ERROR Database connection failed: unable to open database file
```

**Fix**:
1. Check database file exists: `ls -la src/db.sqlite`
2. If not, initialize schema: `cd src && alembic upgrade head && cd ..`
3. Verify write permissions: `touch src/db.sqlite && rm src/db.sqlite`
4. Rerun: `make seed`

### Warning: "Row skipped"

**Example output**:
```
WARN Row 45: Empty owner name (Фамилия), skipping property
WARN Row 52: Invalid decimal format "2,5ab" in Коэффициент, skipping property
```

**Meaning**: Data issue in Google Sheet; specific row ignored but seed continues.  
**Fix**: Review Google Sheet row, correct value, and rerun. (Or data is acceptable as partial seed.)

### Database contains old data after seed

**Symptom**: Expected 20 users, but see 40 (old + new)

**Cause**: Previous seed didn't truncate tables (shouldn't happen)

**Fix**:
```bash
# Manually truncate and retry
sqlite3 src/db.sqlite "DELETE FROM properties; DELETE FROM users;"
make seed
```

### Performance: Seed takes >30 seconds

**Symptom**:
```
[...] INFO   Duration: 45.3 seconds
```

**Cause**: Likely slow network (Google Sheets API latency)

**Fix**:
1. Check internet connection: `ping google.com`
2. Retry: `make seed` (transient network issue)
3. No automatic retry; manual rerun handles transient failures (per design)

## Development Notes

### Running Tests

```bash
# Run all seeding tests
pytest tests/contract/test_seeding_end_to_end.py -v
pytest tests/integration/test_seeding_flow.py -v
pytest tests/unit/test_parsers.py -v

# Run specific test
pytest tests/unit/test_parsers.py::test_parse_russian_decimal -v
```

### Manually Testing Parsers

```python
# From Python REPL
from src.services.parsers import parse_russian_decimal

# Test Russian decimal parsing
parse_russian_decimal("0,5")        # → Decimal('0.5')
parse_russian_decimal("1 000,25")   # → Decimal('1000.25')
parse_russian_decimal("2,9")        # → Decimal('2.9')
```

### Inspecting Google Sheets API Response

```bash
# Enable debug logging (set env var)
DEBUG_GOOGLE_API=1 make seed

# View raw API response (if needed)
python -c "
from src.services.google_sheets import GoogleSheetsClient
client = GoogleSheetsClient()
rows = client.fetch_sheet(os.getenv('GOOGLE_SHEET_ID'), 'Дома')
print(f'Fetched {len(rows)} rows')
print('First row:', rows[0] if rows else 'No rows')
"
```

## Advanced: Seeding Different Data

### Seed from Different Google Sheet

```bash
# Temporarily override GOOGLE_SHEET_ID
GOOGLE_SHEET_ID=YOUR_SHEET_ID make seed

# Or update .env permanently
echo "GOOGLE_SHEET_ID=YOUR_SHEET_ID" >> .env
make seed
```

### Seed Different Sheet Tab

```bash
# Edit src/cli/seed.py and change sheet name
# Default: "Дома"
# Change to: "Дома_backup" or other tab name

# Then rerun
make seed
```

### Dry Run (No Database Changes)

```bash
# Currently not supported; would require additional feature
# For now, use test environment or snapshot database first

# Snapshot current state
cp src/db.sqlite src/db.sqlite.backup

# Run seed
make seed

# Compare or revert
diff <(sqlite3 src/db.sqlite ".dump") <(sqlite3 src/db.sqlite.backup ".dump")
cp src/db.sqlite.backup src/db.sqlite
```

## Offline Operation Requirement

⚠️ **Important**: The seed process **must run when the application is offline** (no running web server or bot).

**Why**: Seeding truncates tables and rebuilds data. Concurrent requests could cause:
- Data inconsistency
- Foreign key violations
- Transaction deadlocks

**Before running seed**:
```bash
# Stop any running servers
Ctrl+C  # (in terminal running FastAPI/bot)

# Verify no connections
lsof -i :8000  # (if empty, good to proceed)
```

## Next Steps

- **Explore data**: Query database to verify imports
- **Run tests**: `pytest tests/` to ensure system works
- **Contribute**: Submit issues or improvements via GitHub

## Support

For issues or questions:
1. Check logs: `cat logs/seed.log`
2. Review [data-model.md](../data-model.md) for entity definitions
3. See [contracts/makefile-interface.md](../contracts/makefile-interface.md) for detailed contract
4. Check specification: [spec.md](../spec.md)

---

**Last updated**: November 10, 2025  
**Tested on**: Python 3.11+, macOS/Linux
