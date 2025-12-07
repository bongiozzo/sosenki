# SOSenki Development Guidelines

Last updated: 2025-12-07

## Core Stack

**Backend:**
- Python 3.11+ (mandatory minimum)
- FastAPI (async API serving)
- FastMCP
- SQLAlchemy ORM + Alembic (migrations)
- SQLite (development database)

**Telegram Integration:**
- `python-telegram-bot` library (async webhooks, bot commands)
- Telegram Web App API (Mini App client-side integration)

**Frontend (Mini App):**
- HTML5/CSS3/JavaScript (Telegram Web App)
- Vanilla JS (no frameworks - keep lightweight)

**External APIs:**
- Google Sheets API (for seeding, configuration)
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

**For running/testing the application, ALWAYS use:**
```bash
make serve &
```

This single command:
- Kills any existing process on port 8000 (prevents process chaos)
- Starts fresh server with your latest code changes
- Uses `uv run` internally for isolated environment
- Starts ngrok tunnel automatically if needed
- Runs in background (`&`) so terminal remains usable

**Never manually start uvicorn, python, or other server processes** - this causes orphaned processes and port conflicts. Always use `make serve &` to ensure clean restarts.

**For other Python commands, use `uv run`:**
- ✅ `uv run pytest tests/` (running tests)
- ✅ `uv run python scripts/script.py` (running scripts)
- ✅ `uv run ruff check .` (linting)
- ❌ Never use `python`, `python3`, or direct execution
- ❌ Never manually activate venv

## Commands Reference

```bash
make serve &  # Run server (ALWAYS use this for testing code changes)
make test     # Run all tests (unit, contract, integration)
make seed     # Reset database + run migrations + seed data
make format   # Run ruff linter
make coverage # Full coverage report
```

## External Library Guidelines

For tasks involving external libraries (Google Sheets, Telegram API, FastAPI, FastMCP, SQLAlchemy):
- **Always query Context7 documentation first** for non-trivial implementations
- Check `/telegram-python-bot`, `/fastapi`, `/sqlalchemy` patterns
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
- [ ] Developer ran `make seed` and verified success
- [ ] No secrets or hard-coded paths in diff
- [ ] Context7 documentation verified for all new dependencies

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
