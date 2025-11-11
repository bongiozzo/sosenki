# SOSenki Project Constitution

<!--
SYNC IMPACT REPORT:
- Version: 1.1.1 → 1.2.0 (MINOR bump: Added No Hard-Coded Paths requirement to Security section - expanded portability and CI/CD safety guidelines)
- Principles Modified: None
- New Requirements: Secret Management section expanded to include No Hard-Coded Paths prohibition
- Security Enhancements: Added dynamic path resolution guidance and rationale for cross-platform/CI compatibility
- Templates: No updates required (guidance applies during code review for all test and source files)
- Compliance Review: Code reviews MUST now flag hard-coded filesystem paths as violations (especially absolute paths)
- Last Amended: 2025-11-11
-->

## Core Principles

### I. YAGNI (You Aren't Gonna Need It)

Build only what is required for the current MVP. Do not speculate about future features or add scaffolding for theoretical use cases. Every line of code MUST serve an immediate, documented user story. Rationale: Reduces cognitive load, speeds time-to-value, prevents technical debt from phantom features.

**YAGNI Rule - Database Schema (NON-NEGOTIABLE)**:

Every database table, column, index, and constraint MUST satisfy the spec.md requirement test: *Can I point to an explicit user story or data flow in spec.md that requires this?* If the answer is no or "maybe for future X," the schema element MUST be removed.

Sub-rules:

1. **No speculative tables or fields**: Do not create tables/fields anticipating future features (e.g., ApprovalNotification table if notifications sent via webhook; RegisteredUser field if User.is_active=True serves the same purpose).

2. **No "future-proofing" entities**: Schema MUST NOT include tables, columns, or indexes designed for hypothetical future features or "just in case" scenarios.

3. **Consolidate over split**: When multiple entities serve the same logical purpose with different names, unify them into a single table with role/flag fields (e.g., Administrator + Client → unified User model with is_administrator, is_investor boolean flags).

4. **Eliminate redundant fields**: If a field can be derived from another field or serves only as documentation (not directly used in queries/logic), remove it (e.g., approved_at is redundant if responded_at already captures the approval timestamp; mini_app_first_opened_at is not required by spec.md so remove it).

5. **No data migration for hypotheticals**: Data migrations MUST NOT preserve/transform old records for features not yet implemented. Start fresh per MVP principle.

6. **Test before adding any index**: Every index MUST map to a documented query pattern in performance considerations or code. Do not add "just in case" indexes.

**Enforcement Checklist** (apply during code review for data-model.md):
- [ ] Every table in schema maps to a section in spec.md user stories
- [ ] Every column has explicit rationale referencing a query or validation rule
- [ ] No "future" columns or "TBD" tables remain
- [ ] No redundant fields (timestamps, derived values) present
- [ ] All indexes correspond to documented query patterns
- [ ] Data migration logic (if any) only handles current feature scope
- [ ] Role/permission logic uses boolean flags, not separate tables

**Rationale**: Schema bloat accumulates technical debt rapidly—every extra table/field increases migration complexity, storage overhead, query planning surface, and maintenance burden. Simplified schemas are faster to migrate, easier to reason about, and scale predictably.

### II. KISS (Keep It Simple, Stupid)

Prefer straightforward solutions over clever implementations. Choose the most readable, maintainable approach even if a complex alternative exists. Code is read far more often than written. Rationale: Simplicity enables faster debugging, onboarding, and feature iteration. Reduces bugs in subtle logic.

### III. DRY (Don't Repeat Yourself)

Eliminate code duplication through abstraction and reuse. When logic appears in multiple places, extract it into a shared module, utility, or service. Document shared dependencies explicitly. Rationale: Single source of truth reduces maintenance burden and ensures consistency across features.

## Technology Stack

### Backend & Core Services

- **Language**: Python 3.11+
- **HTTP Framework**: FastAPI (async-first design for performance)
- **ORM & Migrations**: SQLAlchemy with Alembic (reproducible schema evolution)
- **Database**: SQLite (development) / suitable production replacement per deployment context
- **Task & Dependency Management**: `uv` (package manager and task runner)
- **Telegram Integration**: `python-telegram-bot` library (bot logic and webhook handling)
- **Library Documentation**: MCP Context7 (real-time documentation retrieval for newly added dependencies)

### Frontend

- **Format**: Telegram Bot messages and Mini App Forms (WebApp API on Telegram platform)
- **Delivery**: Served as HTML/CSS/JavaScript from backend HTTP service
- **Rationale**: Single-stack deployment, no separate frontend infrastructure required

### Version Control & Dependency Lock

- **Dependency Declaration**: `pyproject.toml` (single source of truth)
- **Lock File**: `uv.lock` (reproducible installs, required for all environments)
- **Prohibition**: `requirements.txt` MUST NOT be used; all dependencies managed via `uv`
- **Rationale**: Deterministic, auditable, prevents environment drift between dev/prod

## Security Requirements

### Secret Management (NON-NEGOTIABLE)

- **No Hard-Coded Secrets**: All credentials, API keys, database URLs MUST NOT appear in source code
- **No Hard-Coded Paths**: All filesystem paths (especially machine-specific absolute paths like `/Users/...`, `C:\...`) MUST NOT appear in source code. Use dynamic path resolution (e.g., `Path(__file__).parent`) or environment variables for path configuration
- **Environment Variables**: Use only environment variables for secrets in production
- **Local Development**: `.env` files permitted for local development only (never committed)
- **Rationale**: Prevents accidental exposure via version control; enables safe CI/CD integration. Hard-coded paths break tests across different developer machines and CI environments; dynamic resolution ensures portability

## Development Workflow

### Library Documentation Standard (NON-NEGOTIABLE)

- **MCP Context7 Requirement**: When adding new dependencies or libraries to the project, use MCP Context7 to retrieve authoritative, up-to-date documentation
- **Primary Source**: Always fetch current library documentation via Context7 before implementation—do not rely on cached or outdated docs
- **Justification**: Libraries evolve; Context7 ensures developers use current best practices and avoid deprecated APIs
- **Application**: Mandatory when: (a) adding new dependency to `pyproject.toml`, (b) major version upgrades, (c) adopting new library features

### Dependency Management Standards

- **uv Integration**: Use `uv` as primary tool for install, update, and run tasks in both development and production scenarios
- **Documentation**: Development setup MUST reference `uv` installation and common commands (e.g., `uv sync`, `uv run`)
- **CI/CD**: All workflows MUST use `uv` as per Astral documentation best practices

### Testing & Quality Gates

- **Test-First Approach**: Tests written before implementation; red-green-refactor cycle mandatory
- **Scope**: Contract tests for API endpoints, integration tests for user journeys, unit tests for utilities
- **Execution**: All tests MUST pass before PR merge; no skipped or flagged tests

### Code Review Requirements

- **Constitution Compliance**: All reviews verify adherence to YAGNI, KISS, DRY principles
- **Justification**: If complexity is introduced, explicit rationale required in PR description
- **Dependency Changes**: Every new dependency MUST be justified against YAGNI (is it truly necessary?)
- **Schema Design Reviews**: Every data-model.md change MUST pass YAGNI Rule - Database Schema enforcement checklist before approval (see Core Principles)

## Governance

### Amendment Procedure

1. Document proposed amendment with rationale
2. Flag impact on dependent templates (plan-template.md, spec-template.md, tasks-template.md)
3. Produce Sync Impact Report with version bump justification
4. Update all affected templates before merging constitution change

### Versioning Policy

- **MAJOR**: Backward-incompatible principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All PRs/design reviews MUST verify compliance with constitution
- Complexity justification required when code violates YAGNI principle
- `uv` usage verified for Python dependency management across all PRs
- No secrets appear in any diff (automated scan recommended)
- MCP Context7 documentation lookups verified for all new dependencies
- Schema design reviews reference YAGNI Rule - Database Schema enforcement checklist
- Hard-coded filesystem paths (especially absolute paths) are flagged and rejected in code review

**Version**: 1.2.0 | **Ratified**: 2025-11-04 | **Last Amended**: 2025-11-11
