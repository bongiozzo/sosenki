# SOSenki Project Constitution

<!--
SYNC IMPACT REPORT:
- Version: 1.0.0 → 1.1.0 (MINOR bump: Frontend clarification + MCP Context7 documentation standard)
- Principles: No changes (YAGNI, KISS, DRY unchanged)
- Frontend Updated: Clarified as "Telegram Bot Messages and Mini App Forms"
- New Guidance: MCP Context7 mandatory for library documentation lookups
- Templates: No updates required (guidance is tooling standard, not structural change)
- Last Amended: 2025-11-04
-->

## Core Principles

### I. YAGNI (You Aren't Gonna Need It)

Build only what is required for the current MVP. Do not speculate about future features or add scaffolding for theoretical use cases. Every line of code MUST serve an immediate, documented user story. Rationale: Reduces cognitive load, speeds time-to-value, prevents technical debt from phantom features.

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
- **Environment Variables**: Use only environment variables for secrets in production
- **Local Development**: `.env` files permitted for local development only (never committed)
- **Rationale**: Prevents accidental exposure via version control; enables safe CI/CD integration

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

**Version**: 1.1.0 | **Ratified**: 2025-11-04 | **Last Amended**: 2025-11-04
