# Feature Specification: Database Seeding from Google Sheets

**Feature Branch**: `004-database-seeding`  
**Created**: November 10, 2025  
**Status**: Draft  
**Input**: Developer requirement to automate canonical data synchronization from Google Sheets to local development database

## Clarifications

### Session 2025-11-10

- Q: When a new User is created from the sheet data (owner name not found in database), what default role flags should be assigned? → A: Auto-create with is_investor=True, is_administrator=False, is_stakeholder=<based on "Доля в Терра-М" column>. All users have is_investor and is_owner roles by default. is_administrator is set only for Поляков. is_stakeholder is determined by presence of data in "Доля в Терра-М" column.
- Q: How should the system handle Properties with empty, null, or whitespace-only owner names? → A: Skip the row and log a WARNING; include count of skipped rows in final summary. This maintains unattended execution while alerting developers to data quality issues.
- Q: What logging level and output destinations should the seeding process use? → A: INFO level to both stdout and file (logs/seed.log) with WARN/ERROR highlighted. Provides real-time feedback and audit trail while preserving observability.
- Q: When the Google Sheets API call fails (timeout, rate limit, temporary unavailability), how should the seed process respond? → A: Fail immediately with clear error message; no retry. Simplest approach, requires manual re-run for transient failures but prevents masking of persistent configuration issues.
- Q: How should the seeding process manage database transactions during concurrent application access? → A: Document that seed must run when application is offline. This is appropriate for a development tool; clear documentation in Makefile and quickstart establishes operational discipline without unnecessary transaction complexity.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refresh Development Database (Priority: P1)

A developer needs to reset their local development database to match the current state of the canonical master spreadsheet. This ensures all team members have identical, up-to-date data for development and testing without manual intervention.

**Why this priority**: This is the core value of the feature - enabling developers to maintain consistency with the single source of truth (the Google Sheet) in a reproducible way.

**Independent Test**: Can be fully tested by running `make seed` and verifying that the database contains the correct Property and User records that match the sheet "Дома", with proper relational integrity maintained.

**Acceptance Scenarios**:

1. **Given** a fresh developer machine with an empty or outdated database, **When** the developer runs `make seed`, **Then** the database is populated with all Properties and Users from the sheet, correctly linked by owner name.
2. **Given** a database containing stale or incorrect data, **When** `make seed` is run, **Then** all tables are truncated and repopulated with fresh data from the sheet, producing the exact same state as the first seed.
3. **Given** a developer who has run `make seed` once, **When** they run it again immediately, **Then** the database state remains identical (idempotency verified).

---

### User Story 2 - Maintain Configuration-Driven Secrets (Priority: P2)

The seeding process must securely load Google Sheets credentials without storing secrets in the codebase. Configuration (Sheet ID and service account credentials) must be loaded from external files (.env, service_account.json) that are gitignored.

**Why this priority**: Security is critical - hardcoded credentials in source code violates security practices and prevents the feature from being used safely in team environments.

**Independent Test**: Can be tested by verifying that the seeding process loads credentials from external configuration files and succeeds with properly configured credentials, while failing appropriately when credentials are missing.

**Acceptance Scenarios**:

1. **Given** a service account JSON file is placed in the correct location, **When** `make seed` runs, **Then** it successfully authenticates to Google Sheets API and fetches data.
2. **Given** credentials are missing or invalid, **When** `make seed` runs, **Then** it fails with a clear error message and does not attempt to modify the database.
3. **Given** the Google Sheet ID is configured in .env or similar, **When** `make seed` runs, **Then** it fetches data from the correct sheet without requiring code changes.

---

### User Story 3 - Correctly Migrate Properties and Users (Priority: P1)

The seeding script must accurately parse the "Дома" (Houses) sheet and populate the Property and User tables while maintaining relational integrity. Owner names from the sheet must be correctly resolved to User primary keys. If an owner name is not found in the database, a new User is automatically created with default role flags (is_investor=True, is_owner=True, is_administrator=False by default, and is_stakeholder based on "Доля в Терра-М" column presence).

**Why this priority**: Data correctness is fundamental - without proper entity mapping and relational integrity, the database will contain inconsistent or incomplete data.

**Independent Test**: Can be tested by verifying Property records have correct foreign key references to User records, owner names are correctly matched, and all expected properties appear in the database with accurate share weights and statuses. Verify newly created Users have correct default role flags.

**Acceptance Scenarios**:

1. **Given** the "Дома" sheet contains property records with owner names, **When** `make seed` runs, **Then** each Property is correctly linked to the corresponding User via owner_id foreign key.
2. **Given** an owner name appears in the sheet but no corresponding User exists, **When** `make seed` runs, **Then** a new User is created with is_investor=True, is_owner=True, is_administrator=False, and is_stakeholder determined by "Доля в Терра-М" column data, and Properties are correctly linked to this new User.
3. **Given** an owner name is "Поляков", **When** `make seed` runs, **Then** the User record for Поляков has is_administrator=True (and is_investor=True, is_owner=True, is_stakeholder based on column data).
4. **Given** property data includes share weights and status flags, **When** `make seed` runs, **Then** these values are correctly stored in the database (e.g., share_weight as Decimal, is_ready as Boolean).

---

### User Story 4 - Parse Data Types Correctly (Priority: P1)

The seeding script must correctly interpret and convert data types from Google Sheets into appropriate database formats. Russian number formatting (decimal commas, thousand separators) and currency values must be parsed accurately.

**Why this priority**: Data type errors (e.g., storing "р.65 000" as text instead of a Decimal number) would break financial calculations and reporting.

**Independent Test**: Can be tested by verifying that numeric columns are stored as proper numeric types (Decimal, Integer), percentages are parsed correctly (e.g., "3,85%" → 0.0385 or 3.85 depending on storage choice), and currency values have the ruble symbol removed while storing the numeric value.

**Acceptance Scenarios**:

1. **Given** the sheet contains a share weight like "3,85%", **When** `make seed` runs, **Then** it is stored as a numeric value (Decimal) that can be used in calculations.
2. **Given** the sheet contains a price like "р.7 000 000,00", **When** `make seed` runs, **Then** it is stored as a numeric Decimal without the ruble symbol.
3. **Given** the sheet contains "Да"/"Нет" Boolean values, **When** `make seed` runs, **Then** they are correctly converted to True/False in the database.

---

### User Story 5 - Establish Common Make Process (Priority: P2)

The Makefile must include a standardized `make seed` target that encapsulates the entire seeding process. This target should be the single entry point for developers, hiding complexity behind a clear, memorable command.

**Why this priority**: Usability and consistency - a standard Make target ensures all developers use the same process and makes onboarding simpler.

**Independent Test**: Can be tested by running `make seed` and verifying the command completes successfully with proper status messages, and that subsequent runs produce the same database state.

**Acceptance Scenarios**:

1. **Given** a developer's environment with Python, pip dependencies, and database configured, **When** they run `make seed`, **Then** the entire seeding process completes in under 30 seconds.
2. **Given** the Makefile is updated with the `make seed` target, **When** a developer runs `make help`, **Then** the `seed` target is documented with a brief description.
3. **Given** a developer runs `make seed` for the first time, **When** the command completes, **Then** the database is ready for development immediately without additional manual steps.

---

### Edge Cases

- What happens when the Google Sheet is temporarily unavailable or the API rate limit is exceeded? (Fail with clear messaging, not corrupt the database; no automatic retry)
- How does the system handle if a Property row references an owner name that is empty or contains whitespace? (Skip the row, log WARNING, include count in summary)
- What happens when running `make seed` while the application is actively reading from the database? (Seed must run when application is offline; document clearly in Makefile and quickstart)
- What if the "Дома" sheet structure changes (new columns added or removed)? (Script should be resilient to extra columns, may need updates for removed columns)
- What if a Property's share weight is missing or invalid? (Should skip or use a default, with a warning)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `make seed` Makefile target that is the single entry point for the entire seeding process.
- **FR-002**: System MUST fetch data directly from the Google Sheets API using the configured Sheet ID and service account credentials. API calls MUST NOT include automatic retry logic; transient failures will require manual re-execution of the seed command.
- **FR-003**: System MUST NOT read from local CSV or Excel files; API is the exclusive data source.
- **FR-004**: System MUST truncate all data from the `users` and `properties` tables before populating them with fresh data (destructive refresh / truncate-and-load pattern).
- **FR-005**: System MUST correctly parse the "Дома" sheet and map columns to the User and Property models.
- **FR-006**: System MUST resolve owner names from the sheet to corresponding User records by name matching. When creating a new User, system MUST assign: is_investor=True, is_owner=True, is_administrator=False (except for owner name "Поляков" which receives is_administrator=True), and is_stakeholder based on presence of value in "Доля в Терра-М" column.
- **FR-006a**: System MUST map is_stakeholder to User records based on "Доля в Терра-М" column: if owner name has non-empty value in this column, is_stakeholder=True; otherwise is_stakeholder=False.
- **FR-007**: System MUST correctly parse Russian number formatting (decimal commas, thousand separators with spaces) and convert to Python numeric types (Decimal for financial values).
- **FR-008**: System MUST correctly parse currency values (e.g., "р.65 000") by stripping the ruble symbol and converting to Decimal.
- **FR-009**: System MUST correctly parse percentage values (e.g., "3,85%") and store as numeric Decimal.
- **FR-010**: System MUST correctly parse Boolean values from the sheet (e.g., "Да"/"Нет") and store as Python bool.
- **FR-011**: System MUST maintain relational integrity: each Property record MUST have a valid foreign key reference to a User record.
- **FR-012**: System MUST load the Google Sheet ID from external configuration (environment variable or .env file).
- **FR-013**: System MUST load the service account credentials from an external JSON file (not hardcoded).
- **FR-014**: System MUST NOT expose credentials in logs, error messages, or version control.
- **FR-015**: System MUST provide clear error messages if credentials are missing or invalid, explaining the required configuration.
- **FR-016**: System MUST be idempotent: running the seed command N times must result in the exact same database state as running it once.
- **FR-017**: System MUST handle the initial seeding phase to include only the "Дома" sheet (Properties and Users); transaction tables will be handled in a future phase.
- **FR-018**: System MUST provide progress feedback (e.g., logging) during the seeding process so developers know what is happening. Logging MUST use INFO level, output to both stdout and file (logs/seed.log), and highlight WARN/ERROR messages visually for immediate visibility.
- **FR-019**: System MUST handle and report data validation errors gracefully (e.g., if a property has no owner name, log a warning and skip the row).
- **FR-019a**: System MUST skip Properties with empty, null, or whitespace-only owner names ("Фамилия" column). For each skipped row, log a WARNING message with row number and reason. Include a final summary showing total skipped rows and continue processing remaining rows.
- **FR-020**: System MUST complete the seeding process in a reasonable time frame for development (target: under 30 seconds for the current data volume).
- **FR-021**: System MUST document clearly (in Makefile help, quickstart guide, and any user-facing documentation) that the seed command must run when the application is offline. This is appropriate for a development tool and eliminates complex transaction handling.
- **FR-022**: System MUST process the "Доп" (Additional) column. If this column contains a non-empty value, split it by commas. For each comma-separated value, create an additional Property record with the following attributes:
  - **Inherited from main row**: owner_id, is_ready, is_for_tenant
  - **Set to NULL**: share_weight, photo_link, sale_price
  - **Derived from value**: property_name (trimmed value), type (determined by mapping: 26→Малый, 4→Беседка, 69-74→Хоздвор, 49→Склад, others→Баня)
  - **Fixed**: is_active=True
- **FR-023**: System MUST handle empty or whitespace-only values in "Доп" column by treating them as "no additional properties" (no split, no additional records created).

### Key Entities *(include if feature involves data)*

- **User**: Represents a property owner or stakeholder. Key attributes: name (unique identifier), telegram_id (optional, added later), is_active (default=True), is_investor (default=True for all auto-created Users), is_owner (default=True for all auto-created Users), is_administrator (default=False, except owner named "Поляков"=True), is_stakeholder (based on "Доля в Терра-М" column). Relationships: owns multiple Properties.

- **Property**: Represents a physical house or building. Key attributes: property_name, type (Большой/Малый/etc.), share_weight (allocation coefficient), is_active, is_ready, is_for_tenant, photo_link, sale_price. Relationships: owned by a single User.

- **Mapping**: The "Дома" sheet structure maps to these entities:
  - Column "Фамилия" (Owner name) → User.name (creates User if not exists; auto-assign role flags as specified)
  - Column "Дом" (House number) → Property.property_name
  - Column "Размер" (Size) → Property.type
  - Column "Коэффициент" (Coefficient) → Property.share_weight
  - Column "Готовность" (Readiness) → Property.is_ready (Да=True, Нет/empty=False)
  - Column "Аренда" (Rental) → Property.is_for_tenant (Да=True, Нет/empty=False)
  - Column "Фото" (Photo) → Property.photo_link
  - Column "Цена" (Price) → Property.sale_price
  - Column "Доля в Терра-М" (Share) → User.is_stakeholder (presence of value = True, absence = False)
  - Column "Доп" (Additional) → **NEW**: If not empty, split by comma and create additional Property records. Inherited attributes: owner_id, is_ready, is_for_tenant. Set to NULL: share_weight, photo_link, sale_price. Type mapping: 26→Малый, 4→Беседка, 69/70/71/72/73/74→Хоздвор, 49→Склад, all others→Баня.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Single command execution - the seeding process completes with a single `make seed` command, with zero manual steps required post-execution.

- **SC-002**: Idempotency verification - running `make seed` ten consecutive times produces an identical database state each time (verified by comparing record counts and checksums of key fields).

- **SC-003**: Data accuracy - 100% of Property records in the database exactly match the data from the "Дома" sheet (verified by sampling and validation).

- **SC-004**: Relational integrity - 100% of Property records have valid foreign key references to existing User records (verified by constraint checks).

- **SC-005**: Data type correctness - all numeric fields (share_weight, sale_price) are stored as Decimal type and can be used in financial calculations without errors.

- **SC-006**: Performance - the seeding process completes in under 30 seconds for the current data volume (approximately 65 properties and 20 users).

- **SC-007**: Configuration security - credentials are never logged or exposed in error messages; the process fails clearly if credentials are missing.

- **SC-008**: Developer onboarding - a new developer with proper environment setup can run `make seed` and have a fully seeded development database ready for work within 5 minutes.

- **SC-009**: Error reporting - when data validation errors occur (e.g., missing owner, invalid data type), the process logs specific, actionable error messages and completes without corrupting the database.

- **SC-010**: Future extensibility - the first phase handles only the "Дома" sheet; the implementation is structured to allow easy addition of transaction table seeding in phase 2 without refactoring the core framework.

## Assumptions

- The "Дома" sheet in the Google Sheet will maintain a stable structure (columns may be added but existing columns will not be removed or reordered in problematic ways).
- The Google Sheets API is reliably available during development; transient API failures are acceptable (with clear error messaging).
- The service account used for API access has appropriate permissions to read the target Google Sheet.
- Database transactions are properly configured to prevent concurrent access corruption during seeding.
- The `make` command is available in the developer's environment (standard on macOS/Linux; Windows developers should use WSL or equivalent).

## Dependencies & Constraints

- **External Dependencies**: Google Sheets API, google-auth library, sqlalchemy ORM, alembic for migrations.
- **Data Source**: Single Google Sheet identified by ID (configured via `GOOGLE_SHEET_ID` env var); Sheet named "Дома" within the workbook.
- **Credentials**: Service account JSON file referenced via `GOOGLE_CREDENTIALS_PATH` environment variable in `.env` file.
- **Scope**: Initial implementation handles only User and Property entities from the "Дома" sheet; transaction/payment tables (from other sheets like "Траты-25/2") are explicitly out of scope for this phase.
- **Database Constraint**: Must maintain schema compatibility with existing SQLAlchemy models (User, Property).

## Open Questions

- Should we implement data validation for Properties with missing share weights? (Current assumption: log warning and skip or use default, to be determined during planning)
