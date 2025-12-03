# SOSenki Development Guidelines

Last updated: 2025-11-24

## Core Stack

**Backend:**
- Python 3.11+ (mandatory minimum)
- FastAPI (async API serving)
- SQLAlchemy ORM + Alembic (migrations)
- SQLite (development database)

**Telegram Integration:**
- `python-telegram-bot` library (async webhooks, bot commands)
- Telegram Web App API (Mini App client-side integration)

**Frontend (Mini App):**
- HTML5/CSS3/JavaScript (Telegram Web App)
- Vanilla JS (no frameworks - keep lightweight)

**External APIs:**
- Google Sheets API (seeding, configuration)
- Google Auth (credentials management)

**Testing & Quality:**
- pytest (unit, contract, integration tests)
- pytest-asyncio (async test support)
- pytest-cov (coverage analysis)
- ruff (linting)
- mypy (type checking)

## Project Structure

```text
src/
  api/              # FastAPI endpoints (mini_app.py, webhook.py)
  bot/              # Telegram bot handlers
  models/           # SQLAlchemy models
  services/         # Business logic services
  static/mini_app/  # Frontend (HTML/CSS/JS)
tests/
  unit/             # Unit tests
  contract/         # API contract tests
  integration/      # Full workflow tests
seeding/            # Data seeding utilities (Google Sheets integration)
```

## Python Execution - CRITICAL

**ALWAYS use `uv run` for ANY Python command execution:**
- ✅ `uv run pytest tests/` (running tests)
- ✅ `uv run python scripts/script.py` (running scripts)
- ✅ `uv run ruff check .` (linting)
- ❌ Never try `python`, `python3`, or direct execution
- ❌ Never manually activate venv (uv handles this)

This ensures:
1. Correct isolated environment
2. Proper dependency management
3. Consistent behavior across machines
4. No version conflicts

## Commands Reference

```bash
uv run pytest tests/                          # Run all tests
uv run pytest tests/ --cov=src                # Run with coverage
uv run ruff check .                           # Lint check
uv run ruff check . --fix                     # Auto-fix lint issues
cd src && uv run alembic revision --autogenerate -m "message"  # Create migration
cd src && uv run alembic upgrade head         # Apply migrations
make coverage                                 # Full coverage report (uses uv run)
```

## External Library Guidelines

For tasks involving external libraries (Google Sheets, Telegram API, FastAPI, SQLAlchemy):
- **Always query Context7 documentation first** for non-trivial implementations
- Check `/google-api-python-client`, `/fastapi`, `/sqlalchemy` patterns
- Validate API signatures against Context7 before coding
- This prevents outdated code patterns and API mismatches

## Code Style

**Python 3.11+ conventions:**
- Type hints (mandatory for all functions)
- Async/await for I/O operations
- Pydantic models for data validation
- SQLAlchemy ORM best practices
- Docstrings for classes and public methods
- Follow ruff linter recommendations (auto-fixable with `uv run ruff check . --fix`)

## Core Principles

### I. YAGNI (You Aren't Gonna Need It)

Build only what is required for the current MVP. Every line of code MUST serve an immediate, documented user story. Do not speculate about future features or add scaffolding for theoretical use cases.

**Database Schema - YAGNI Rules (NON-NEGOTIABLE):**
- Every table, column, index must satisfy: *Can I point to an explicit user story in spec.md that requires this?*
- No speculative tables/fields anticipating future features
- No "future-proofing" entities or redundant fields (e.g., remove derived timestamps)
- Consolidate entities with different names into unified models with role/flag fields
- Maintain single `001_initial_schema.py` migration reflecting complete current MVP schema
- Modify `001_initial_schema.py` directly when schema changes—do NOT create separate migration files
- After updates, verify with `make db-reset && make seed`
- Test before adding any index; every index MUST map to a documented query pattern

### II. KISS (Keep It Simple, Stupid)

Prefer straightforward solutions over clever implementations. Choose the most readable, maintainable approach even if complex alternatives exist. Code is read far more often than written.

### III. DRY (Don't Repeat Yourself)

Eliminate code duplication through abstraction and reuse. When logic appears in multiple places, extract it into a shared module, utility, or service. Document shared dependencies explicitly.

## Security & Configuration

**Secret Management (NON-NEGOTIABLE):**
- No hard-coded secrets, API keys, or credentials in source code
- No hard-coded filesystem paths (especially absolute paths like `/Users/...`, `C:\...`)
- Use environment variables for secrets in production; `.env` for local development only (never committed)
- Use dynamic path resolution (e.g., `Path(__file__).parent`) instead of machine-specific paths

## Development Standards

**Testing Approach:**
- Test-first: write tests before implementation (red-green-refactor cycle)
- Scope: contract tests for API endpoints, integration tests for workflows, unit tests for utilities
- All tests MUST pass before PR merge; no skipped or flagged tests

**Code Review Checklist:**
- [ ] Constitution compliance verified (YAGNI, KISS, DRY adherence)
- [ ] Schema design follows YAGNI Rule - Database Schema (every table/column justified by spec.md)
- [ ] No separate migration files created (`001_initial_schema.py` modified directly only)
- [ ] Developer ran `make db-reset && make seed` and verified success
- [ ] No secrets or hard-coded paths in diff
- [ ] Context7 documentation verified for all new dependencies

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
