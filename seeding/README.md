# SOSenki Database Seeding

This folder contains all database seeding functionality separated from the main application code.

## Structure

```
seeding/
  ├── cli/
  │   ├── __init__.py
  │   └── seed.py          # CLI entry point for seeding command
  ├── core/
  │   ├── __init__.py
  │   ├── seeding.py           # Main orchestrator
  │   ├── seeding_utils.py     # Common utilities
  │   ├── seeding_config.py    # Configuration loader (moved from src)
  │   ├── google_sheets.py     # Google Sheets API client
  │   ├── bills_seeding.py     # Bills data parser
  │   ├── credit_seeding.py    # Credit transactions parser
  │   ├── debit_seeding.py     # Debit transactions parser
  │   ├── electricity_seeding.py
  │   ├── property_seeding.py  # Properties parser
  │   ├── shared_electricity_bill_seeding.py
  │   └── transaction_seeding.py
  ├── config/
  │   ├── __init__.py
  │   ├── seeding.json         # Actual configuration (not in git)
  │   └── seeding.json.example # Template with documentation
  └── README.md                # This file
```

## Quick Start

### 1. Setup Configuration

Copy the example configuration to create your actual configuration:

```bash
cp seeding/config/seeding.json.example seeding/config/seeding.json
```

### 2. Customize Configuration

Edit `seeding/config/seeding.json`:
- Update `range_name` values to match your Google Sheets named ranges
- Update column names to match your Google Sheets headers
- Add special rules for specific users if needed
- Define service periods for your billing cycles

### 3. Setup Google Credentials

Create a service account and download credentials:

```bash
# Create service account at:
# https://console.cloud.google.com/iam-admin/serviceaccounts

# Download JSON key file
# Save as: credentials.json (NOT in git)

# Share your Google Sheet with the service account email
```

Set environment variable:
```bash
export GOOGLE_CREDENTIALS_PATH="credentials.json"
export SEEDING_CONFIG_PATH="seeding/config/seeding.json"
```

Or add to `.env`:
```
GOOGLE_CREDENTIALS_PATH=credentials.json
SEEDING_CONFIG_PATH=seeding/config/seeding.json
```

### 4. Run Seeding

The Makefile target works from the root:

```bash
make seed
```

Or directly:

```bash
uv run python -m seeding.cli.seed
```

## Configuration Guide

### Named Ranges

Create named ranges in Google Sheets (Data > Named ranges):

- `PropertiesOwners` - Main data with users and properties
- `Debit2425` - Debit transactions for 2024-2025 period
- `Credit2425` - Credit transactions for 2024-2025 period
- `Elec2425` - Electricity readings for 2024-2025 period
- etc.

### Column Names

All column names in `fields.parsing` must match Google Sheets headers EXACTLY (case-sensitive).

Example:

```json
"fields": {
  "parsing": {
    "name_column": "LastName",
    "stakeholder_column": "Share"
  }
}
```

Google Sheets must have headers:

- Column A: "LastName"
- Column B: "Share"
- etc.

### Split Handling

To split ownership or bills between multiple users, use "/" in user names:

```
Google Sheets row: "Ivanov/Petrov"
Configuration:
{
  "transformations": {
    "name_based_rules": {
      "Ivanov/Petrov": {
        "Ivanov": 0.5,
        "Petrov": 0.5
      }
    }
  }
}
```

Each user gets their own record with proportional amounts.

### Service Periods

Define billing cycles in `service_periods`:

```json
"service_periods": {
  "2024-2025": {
    "start_date": "01.07.2024",
    "end_date": "01.07.2025"
  }
}
```

Then reference them from transaction schemas:

```json
"debit_transactions": {
  "service_periods": {
    "Debit2425": "2024-2025"
  }
}
```

## Data Import Process

The seeding process executes in this order:

1. **Fetch** - Read data from Google Sheets using named ranges
2. **Parse Users** - Extract and validate user data
3. **Parse Properties** - Extract and validate property data
4. **Create Users** - Insert users into database
5. **Create Properties** - Insert properties linked to users
6. **Create Service Periods** - Insert billing cycle definitions
7. **Create Transactions** - Import debits and credits
8. **Create Readings** - Import electricity readings
9. **Create Bills** - Import shared and regular bills
10. **Commit** - All-or-nothing atomic transaction

If any step fails, the entire transaction is rolled back.

## Record Counts

After seeding completes successfully, a summary shows record counts:

```
✓ Seed successful
  Users: 42
  Properties: 128
  Debits: 256
  Credits: 89
  Electricity readings: 84
  Electricity bills: 21
  Shared electricity bills: 15
  Bills (conservation/main): 178
  Skipped: 3
```

## Troubleshooting

### "Configuration not found"

```
ERROR: Seeding configuration not found at seeding/config/seeding.json
```

Solution: Copy and customize the example:
```bash
cp seeding/config/seeding.json.example seeding/config/seeding.json
```

### "Range not found"

```
ERROR: Sheet not found or range 'PropertiesOwners' not found
```

Solutions:
1. Check named range name in Google Sheets (Data > Named ranges)
2. Verify spelling matches `range_name` in config
3. Ensure service account has access to sheet

### "Credentials file not found"

```
ERROR: Credentials file not found: credentials.json
```

Solution:
```bash
# Create service account and download JSON key
# https://console.cloud.google.com/iam-admin/serviceaccounts
# Save to credentials.json
# Set environment variable:
export GOOGLE_CREDENTIALS_PATH="credentials.json"
```

### "Access denied"

```
ERROR: Access denied to sheet [ID]. Check service account permissions.
```

Solution: Share Google Sheet with service account email found in credentials.json

## Production Usage

### Security

**Important:** Do NOT commit `seeding/config/seeding.json` to git - it contains personal/commercial data.

Add to `.gitignore`:
```
seeding/config/seeding.json
credentials.json
```

### Idempotency

Seeding is idempotent - running twice produces the same result:
1. Existing tables are truncated
2. All data is re-imported fresh
3. Safe to run multiple times

### Community Documentation

This seeding functionality is designed for community transparency:
- Configuration-driven (no hardcoded values)
- Commented examples in `.json.example` files
- Clear orchestration in `seeding.py`
- Suitable for communities managing shared properties

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEEDING_CONFIG_PATH` | `seeding/config/seeding.json` | Path to configuration file |
| `GOOGLE_CREDENTIALS_PATH` | (required) | Path to Google service account JSON key |
| `DATABASE_URL` | `sqlite:///sosenki.db` | Database connection string |

## See Also

- `seeding/config/seeding.json.example` - Configuration template with examples
- `Makefile` - Run `make seed` to start seeding
- `tests/seeding/` - Test cases for seeding functionality
