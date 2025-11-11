# Data Model: Database Seeding

**Phase**: 1 (Design) | **Date**: November 10, 2025  
**References**: [spec.md](spec.md) | [plan.md](plan.md) | [research.md](research.md)

## Entity Definitions

### User Entity

**Purpose**: Represents owners of properties from the "Дома" sheet.  
**Storage**: Existing SQLAlchemy model at `src/models/user.py`  
**Mapping**: One row per unique owner name from "Фамилия" column

#### Attributes

| Attribute | Type | Source Column | Default | Validation |
|-----------|------|---------------|---------|-----------|
| `id` | Integer | (auto-generated) | — | Primary key, not null |
| `name` | String(255) | "Фамилия" | — | Not null, unique, non-empty |
| `telegram_id` | Integer | (not in sheet) | NULL | Optional, unique if provided |
| `is_active` | Boolean | (not in sheet) | True | Not null |
| `is_investor` | Boolean | (role default) | True | Not null |
| `is_owner` | Boolean | (role default) | True | Not null |
| `is_administrator` | Boolean | (conditional) | False → True if name == "Поляков" | Not null |
| `is_stakeholder` | Boolean | (conditional) | True if "Доля в Терра-М" has value, else False | Not null |
| `created_at` | DateTime | (auto-generated) | server_default=now() | Not null |
| `updated_at` | DateTime | (auto-generated) | server_default=now() | Not null |

#### Parsing Rules

```python
def parse_user_row(row):
    """
    Parse a row from "Дома" sheet into User entity.
    
    Input: Dictionary with keys like "Фамилия", "Доля в Терра-М"
    Output: User instance ready for insert
    
    Rules:
    1. name = row["Фамилия"].strip()
    2. if not name: SKIP (log WARNING, count in summary)
    3. is_investor = True (always)
    4. is_owner = True (always)
    5. is_administrator = True only if name == "Поляков" (exact match)
    6. is_stakeholder = True if row.get("Доля в Терра-М", "").strip() else False
    7. telegram_id = None (not in sheet, can be set via bot later)
    8. is_active = True (new users are active by default)
    """
```

#### State Transitions

```
CREATION (during seed):
  ┌─────────────────────────────────────────┐
  │ Google Sheet row parsed                 │
  ├─────────────────────────────────────────┤
  │ name NOT empty → INSERT User            │
  │ Role flags: investor=✓ owner=✓ admin=?  │
  │ stakeholder based on share column       │
  └─────────────────────────────────────────┘
         ↓
  User in database (is_active=True)

UPDATES (via bot, not in seeding):
  - telegram_id set when user interacts with bot
  - is_active toggled by administrator
  - Other role flags managed by business logic
  - Updated_at timestamp auto-set by ORM
```

#### Uniqueness Constraints

- `name` UNIQUE: Only one user per owner name (enforced by SQLAlchemy unique=True)
- `telegram_id` UNIQUE if not NULL: At most one telegram account per user
- Seed process lookup: Query by name (case-sensitive); fail if exists
- Collision handling: Log ERROR, exit seed with code 1

### Property Entity

**Purpose**: Represents individual properties (houses/apartments) from the "Дома" sheet.  
**Storage**: Existing SQLAlchemy model at `src/models/property.py`  
**Mapping**: One row per record in "Дома" sheet (including multi-property owners)

#### Attributes

| Attribute | Type | Source Column | Default | Validation |
|-----------|------|---------------|---------|-----------|
| `id` | Integer | (auto-generated) | — | Primary key, not null |
| `owner_id` | Integer | "Фамилия" | — | Foreign key → User.id, not null |
| `property_name` | String(255) | "Дом" | — | Not null, non-empty |
| `type` | String(50) | "Размер" | — | Enum: Большой, Малый, Гаражное место, etc. |
| `share_weight` | Decimal(5,2) | "Коэффициент" | — | Not null, must be parseable as Russian decimal |
| `is_active` | Boolean | (not in sheet) | True | Not null |
| `is_ready` | Boolean | "Готовность" | False → True if "Да" | Not null |
| `is_for_tenant` | Boolean | "Аренда" | False → True if "Да" | Not null |
| `photo_link` | String(500) | "Фото" | NULL | Optional, URL format |
| `sale_price` | Decimal(12,2) | "Цена" | NULL | Optional, must be parseable as Russian decimal |
| `created_at` | DateTime | (auto-generated) | server_default=now() | Not null |
| `updated_at` | DateTime | (auto-generated) | server_default=now() | Not null |

#### Parsing Rules

```python
def parse_property_row(row, user_lookup):
    """
    Parse a row from "Дома" sheet into Property entity.
    
    Input: 
      - Dictionary with keys like "Дом", "Фамилия", "Коэффициент", etc.
      - user_lookup: Dict[name] → User for owner resolution
    Output: List of Property instances ready for insert (main + additional from "Доп")
    
    Rules:
    1. owner_name = row["Фамилия"].strip()
    2. if not owner_name: SKIP row (handled by User parsing, log WARNING)
    3. owner_id = user_lookup.get(owner_name).id
    4. property_name = row["Дом"].strip() (no empty check; allow any value)
    5. type = row["Размер"].strip() (no validation; store as-is)
    6. share_weight = parse_russian_decimal(row["Коэффициент"])
    7. is_ready = row["Готовность"].strip().lower() == "да"
    8. is_for_tenant = row["Аренда"].strip().lower() == "да"
    9. photo_link = row.get("Фото", "").strip() or None
    10. sale_price = parse_russian_decimal(row.get("Цена", "")) or None
    11. is_active = True (new properties are active by default)
    
    NEW (Additional properties from "Доп" column):
    12. dop_value = row.get("Доп", "").strip()
    13. if dop_value:
        a. Split dop_value by comma to get list of values
        b. For each value in list:
           - value = value.strip()
           - property_name = value
           - type = determine_type(value) using mapping:
             * "26" → "Малый"
             * "4" → "Беседка"
             * "69", "70", "71", "72", "73", "74" → "Хоздвор"
             * "49" → "Склад"
             * all others → "Баня"
           - owner_id = same as main row (inherited)
           - is_ready = same as main row (inherited)
           - is_for_tenant = same as main row (inherited)
           - share_weight = None (NULL)
           - photo_link = None (NULL)
           - sale_price = None (NULL)
           - is_active = True
           - Create new Property instance
    14. Return list containing main Property plus all additional Properties
    """
```

#### Parsing Helper: Russian Decimal Conversion

```python
def parse_russian_decimal(value_str):
    """
    Parse Russian-formatted decimal strings.
    
    Input formats:
      - "0,5" → Decimal('0.5')
      - "1 000,25" → Decimal('1000.25')
      - "2,9" → Decimal('2.9')
      - "" or None → raise ValueError
    
    Algorithm:
    1. Strip whitespace
    2. Remove space (thousand separator)
    3. Replace comma with period
    4. Parse as float, convert to Decimal
    5. On error, raise ValueError with original string
    
    Exceptions raised: ValueError (caller must handle)
    """
```

#### State Transitions

```
CREATION (during seed):
  ┌──────────────────────────────────────────────┐
  │ Google Sheet row parsed                      │
  ├──────────────────────────────────────────────┤
  │ Look up owner by name in User table          │
  │ Parse decimal fields (Коэффициент, Цена)    │
  │ Map boolean fields (Готовность, Аренда)     │
  │ Build Property with owner_id reference       │
  └──────────────────────────────────────────────┘
         ↓
  Property in database (is_active=True, created_at=now)

UPDATES (via business logic, not in seeding):
  - is_active toggled by administrator
  - share_weight updated if property classification changes
  - is_ready updated based on actual status
  - Updated_at timestamp auto-set by ORM
```

#### Foreign Key Constraint

- `owner_id` → `User.id` (ON DELETE CASCADE per SQLAlchemy convention)
- Seed process: Owner User must exist before Property insert
- Lookup failure: Log ERROR, exit seed with code 1 (data integrity issue)

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Google Sheet "SosenkiPrivate" / Sheet "Дома"               │
├─────────────────────────────────────────────────────────────┤
│ Columns: Фамилия | Дом | Размер | Коэффициент | ...        │
│ Rows: 65 properties across ~20 unique owners               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ (1) Fetch via Google Sheets API
                         │     (service account auth)
                         ▼
        ┌────────────────────────────────────┐
        │ Raw Sheet Data (list of dicts)     │
        │ Each dict = one row                │
        └────────────┬───────────────────────┘
                     │
                     │ (2a) Parse & deduplicate owners
                     │     (group by "Фамилия")
                     ▼
        ┌────────────────────────────────────┐
        │ User entities                      │
        │ - Parse owner name                 │
        │ - Assign role flags (investor,     │
        │   owner, admin conditional,        │
        │   stakeholder conditional)         │
        │ - Skip if empty name (WARNING)    │
        └────────────┬───────────────────────┘
                     │
                     │ (3) Database Transaction BEGIN
                     │
        ┌────────────▼───────────────────────┐
        │ (3a) TRUNCATE users table          │
        │ (3b) TRUNCATE properties table     │
        │ (3c) INSERT all User entities      │
        │      (with ON CONFLICT handling?)  │
        └────────────┬───────────────────────┘
                     │
                     │ (2b) Parse all properties
                     │      (with owner_id lookup)
                     ▼
        ┌────────────────────────────────────┐
        │ Property entities                  │
        │ - Parse numeric fields (Russian)  │
        │ - Resolve owner_id via lookup      │
        │ - Map boolean fields               │
        │ - Fail if owner not found          │
        │ - NEW: Split "Доп" column by comma │
        │   and create additional records    │
        │   with type mapping (26→Малый,     │
        │   4→Беседка, 69-74→Хоздвор,       │
        │   49→Склад, other→Баня)            │
        │ - Each additional record inherits  │
        │   owner_id, share_weight, etc.     │
        └────────────┬───────────────────────┘
                     │
        ┌────────────▼───────────────────────┐
        │ (3d) INSERT all Property entities  │
        │      (main + additional from "Доп")
        │ (3e) COMMIT transaction            │
        │ (3f) Return seed summary           │
        └────────────┬───────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────┐
        │ SQLite Database                    │
        │ - users: N unique owner names      │
        │ - properties: 65+ records          │
        │   (65 main + additional from "Доп")
        │ - All foreign keys valid           │
        └────────────────────────────────────┘
                     │
                     │ (4) Log results to seed.log
                     │     + stdout (INFO level)
                     ▼
        ┌────────────────────────────────────┐
        │ Seed Summary                       │
        │ - Users created: N                 │
        │ - Properties created: 65+M         │
        │   (M = additional from "Доп")      │
        │ - Rows skipped: K (with reasons)   │
        │ - Duration: T seconds              │
        │ - Status: SUCCESS or FAIL          │
        └────────────────────────────────────┘
```

## Validation Rules

### User Validation

| Rule | Source | Enforcement | Severity |
|------|--------|-------------|----------|
| Non-empty name | spec.md FR-006 | Row-level, log WARNING | Skip row |
| Unique name | database constraint | Transaction-level | FAIL seed |
| Valid role assignment logic | spec.md Q&A answer | Code-level (parse_user_row) | Code review |

### Property Validation

| Rule | Source | Enforcement | Severity |
|------|--------|-------------|----------|
| Owner exists | FK constraint | Transaction-level | FAIL seed |
| Valid Russian decimals | parsers.py | Row-level, log WARNING | Skip row |
| Non-empty property_name | (implicit) | Allow any | (no skip) |

## Edge Cases & Resolution

### Edge Case 1: Empty Owner Name in "Фамилия" Column
- **Scenario**: Row has empty or whitespace-only value for "Фамилия"
- **Detection**: `name = row["Фамилия"].strip(); if not name:`
- **Action**: SKIP property row, log WARNING with row number
- **Count**: Increment skipped_empty_owner counter
- **Result**: Property never inserted; seeded User count unchanged
- **Justification** (spec.md Q2): Partial seed better than complete failure

### Edge Case 2: Duplicate Owner Names
- **Scenario**: Two properties list the same owner name (expected, handled correctly)
- **Detection**: `user_lookup.get(owner_name)` returns same User for multiple properties
- **Action**: All properties reference same owner_id (correct)
- **Result**: One User, multiple Properties with owner_id=User.id
- **Justification**: This is normal; one owner can have multiple properties

### Edge Case 3: Owner Name Collision (Name Exists in Database)
- **Scenario**: Seeding a second time; users table still has previous seed
- **Detection**: TRUNCATE handles this; all previous users deleted before insert
- **Action**: Idempotency ensured; seed twice → same result
- **Result**: Clean replacement, no unique constraint violations
- **Justification** (research.md): Truncate-and-load pattern

### Edge Case 4: Invalid Russian Decimal Format
- **Scenario**: "Коэффициент" or "Цена" column contains non-numeric or unparseable text
- **Detection**: `parse_russian_decimal()` raises ValueError
- **Action**: Catch exception, log WARNING with original value
- **Count**: Increment skipped_invalid_decimal counter
- **Result**: Property row skipped; seeded Property count unchanged
- **Justification** (research.md): Skip on validation error, fail-fast on API error

### Edge Case 5: Empty "Доля в Терра-М" Column
- **Scenario**: Owner row has empty or whitespace-only value for stakeholder indicator
- **Detection**: `row.get("Доля в Терра-М", "").strip()`
- **Action**: Evaluate as False; set is_stakeholder=False
- **Result**: User created with is_stakeholder=False
- **Justification** (spec.md Q&A): If no share value, not a stakeholder

### Edge Case 6: Special Characters in Property Name or Type
- **Scenario**: "Дом" or "Размер" columns contain Cyrillic, numbers, or special chars
- **Detection**: No validation; stored as-is
- **Action**: Store raw string from sheet
- **Result**: No skip; all characters preserved in database
- **Justification**: Sheet is source of truth; preserve exact values

### Edge Case 7: Empty "Доп" Column
- **Scenario**: "Доп" column is empty, whitespace-only, or missing for a row
- **Detection**: `row.get("Доп", "").strip()` evaluates to empty string
- **Action**: No additional properties created; only main property inserted
- **Result**: Main property row processed normally; count unchanged
- **Justification** (spec.md FR-023): Empty "Доп" means no additional properties

### Edge Case 8: "Доп" Column with Single Value (No Comma)
- **Scenario**: "Доп" column contains a single value like "26" (no comma separator)
- **Detection**: Split by comma results in list with one element
- **Action**: Create one additional property record with property_name="26", type determined by mapping
- **Result**: Two properties total for this owner from this row (main + one additional)
- **Justification**: Same logic as multi-value case; comma-split handles both

### Edge Case 9: "Доп" Column with Multiple Values (With Commas)
- **Scenario**: "Доп" column contains comma-separated values like "26, 4, 49"
- **Detection**: Split by comma results in list with multiple elements
- **Action**: Create one additional property record per value
- **Result**: Four properties total for this owner from this row (main + three additional)
- **Justification** (spec.md FR-022): Each comma-separated value creates a new record

### Edge Case 10: "Доп" Column with Unknown Type Code
- **Scenario**: "Доп" column contains value not in type mapping (e.g., "99", "ABC")
- **Detection**: Value not in [26, 4, 69-74, 49] set
- **Action**: Map to default type "Баня"
- **Result**: Additional property created with type="Баня"
- **Justification** (spec.md FR-22): Default type for unmapped codes is "Баня"

### Edge Case 11: "Доп" Column with Whitespace-Padded Values
- **Scenario**: "Доп" column contains " 26 , 4 , 49 " with extra spaces around commas
- **Detection**: Split by comma, then strip each value
- **Action**: Strip each value before type mapping; trim and normalize
- **Result**: Additional properties created correctly with normalized values
- **Justification**: User data entry may include accidental whitespace; normalize consistently

### Edge Case 12: Additional Property Attributes (Partial Inheritance)
- **Scenario**: Additional property created from "Доп" column value
- **Detection**: Additional property record constructed
- **Action**: 
  - **Inherit**: owner_id, is_ready, is_for_tenant (same as main row)
  - **Set to NULL**: share_weight, photo_link, sale_price
  - **Set explicitly**: property_name (from "Доп" value), type (from type mapping)
- **Result**: Additional property has same owner/readiness/tenant status, but no share_weight or pricing information
- **Justification** (user requirement): Additional properties are auxiliary structures without independent allocation weight or pricing

## Database Constraints (Existing Schema)

### User Table Constraints
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    telegram_id INTEGER UNIQUE,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_investor BOOLEAN NOT NULL,
    is_owner BOOLEAN NOT NULL,
    is_administrator BOOLEAN NOT NULL,
    is_stakeholder BOOLEAN NOT NULL,
    created_at DATETIME DEFAULT (now()) NOT NULL,
    updated_at DATETIME DEFAULT (now()) NOT NULL
);
```

### Property Table Constraints
```sql
CREATE TABLE properties (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    share_weight NUMERIC(5,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_ready BOOLEAN NOT NULL,
    is_for_tenant BOOLEAN NOT NULL,
    photo_link VARCHAR(500),
    sale_price NUMERIC(12,2),
    created_at DATETIME DEFAULT (now()) NOT NULL,
    updated_at DATETIME DEFAULT (now()) NOT NULL
);
```

## Seeding Sequence (Transaction Atomicity)

```python
def seed_database():
    """Entire seeding process in single transaction."""
    session = create_session()
    try:
        # Phase 1: Fetch from Google Sheets API
        rows = fetch_from_google_sheets()  # May raise: AuthError, APIError
        
        # Phase 2: Parse rows into entities (no DB writes yet)
        users, properties = parse_rows(rows)  # May raise: ValueError (skip row)
        
        # Phase 3: Atomic database operations
        with session.begin():  # Transaction starts
            # Clear existing data
            session.query(Property).delete()
            session.query(User).delete()
            
            # Insert new data
            session.add_all(users)
            session.flush()  # Assign IDs but don't commit
            
            session.add_all(properties)
            session.flush()
            
            # Validate: Check FK constraints
            validate_relationships(session)
            
        # Transaction commits here; all-or-nothing
        
        # Phase 4: Generate summary
        return generate_summary(users, properties)
        
    except AuthError:
        log.error("Google Sheets API auth failed")
        session.rollback()
        return FAIL
    except APIError:
        log.error("Google Sheets API request failed")
        session.rollback()
        return FAIL
    except ValueError as e:
        log.warning(f"Skipped row: {e}")
        # Continue to next row; don't rollback
        return PARTIAL_SUCCESS
    finally:
        session.close()
```

## Success Criteria Validation

| Criterion | Data Model Support | Verification |
|-----------|------------------|--------------|
| Single command execution | ✅ CLI entry point triggers entire flow | `make seed` |
| Idempotent | ✅ Truncate-and-load atomicity | Run twice: same result |
| 100% data accuracy | ✅ Direct mapping User/Property fields | Schema matches spec.md Key Entities |
| Relational integrity | ✅ FK constraints + transaction isolation | `owner_id` always valid |
| <30s performance | ✅ Batch insert, no loops | Benchmark with 65 properties |
| Clear feedback | ✅ INFO logs + summary statistics | Parse errors logged as WARN |
| Secure credentials | ✅ External JSON file, no hardcoding | Credentials not in code |

## References

- **Specification**: [spec.md](spec.md) - User Stories US-001 to US-005, FR-006 to FR-021
- **Research**: [research.md](research.md) - Technical decisions on parsing, transactions, logging
- **Constitution**: [constitution.md](./.specify/memory/constitution.md) - YAGNI, KISS, DRY principles
- **Existing Models**: 
  - User: `src/models/user.py`
  - Property: `src/models/property.py`
