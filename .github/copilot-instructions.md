# SOSenki Development Guidelines

Last updated: 2025-12-20

## Architecture Overview

**Three-tier system:**
1. **Telegram Bot** (`src/bot/`) — User-facing interface via commands and callbacks
2. **Mini App** (`src/static/mini_app/`) — Web UI served inside Telegram (vanilla JS, no frameworks)
3. **FastAPI Backend** (`src/api/`) — REST endpoints + webhook receiver + MCP server

**Core Stack:**
- Python 3.11+ (mandatory minimum)
- FastAPI (async API serving)
- FastMCP (LLM tool server - provides `get_balance`, `list_bills`, `create_service_period`)
- SQLAlchemy ORM + Alembic (migrations in `alembic/versions/`)
- SQLite (development: `sosenki.dev.db`, production: `sosenki.db`, test: `test_sosenki.db`)
- `python-telegram-bot` (async webhooks, bot commands)
- Ollama (local LLM for `/ask` command tool-calling)
- Google Sheets API (for seeding/configuration)
- Vanilla JS (Mini App frontend — no frameworks, keep lightweight)
- `uv` (Python package manager — replaces pip/venv)

**Testing:**
- pytest (unit, contract, integration tests)
- pytest-asyncio (async test support)
- pytest-cov (coverage analysis)
- ruff (linting & formatting)

## Project Structure

```text
src/
  api/              # FastAPI endpoints
    mini_app.py     # Mini App REST API (user context, bills, transactions)
    webhook.py      # Telegram webhook receiver + FastAPI app setup
    mcp_server.py   # FastMCP tool server (get_balance, list_bills, create_service_period)
  bot/              # Telegram bot handlers
    handlers/       # Command/callback handlers (/start, /request, admin flows)
    config.py       # Bot configuration + application builder
  models/           # SQLAlchemy ORM models (User, Account, Bill, ServicePeriod, etc.)
  services/         # Business logic layer
    auth_service.py       # Telegram auth + user context resolution
    balance_service.py    # Balance calculation logic
    bills_service.py      # Bill management and processing
    transaction_service.py # Transaction CRUD operations
    period_service.py     # ServicePeriod CRUD operations
    llm_service.py        # Ollama integration + tool execution
    localizer.py          # i18n with flat key convention (see i18n section)
    locale_service.py     # Currency/datetime formatting for Russian locale
  static/mini_app/  # Frontend (HTML/CSS/JS + translations.json)
  prompts/          # LLM system prompts (.prompt.md files)
alembic/versions/   # Database migrations (Alembic)
tests/
  unit/             # Unit tests (services, models, utilities)
  contract/         # API contract tests (endpoint schemas, MCP tools)
  integration/      # Full workflow tests (end-to-end scenarios)
seeding/            # Data seeding utilities (Google Sheets integration)
scripts/            # Maintenance scripts (check_translations.py, analyze_dead_code.py)
```

## Python Execution - CRITICAL (NON-NEGOTIABLE)

### ⚠️ MANDATORY RULES FOR AI AGENTS ⚠️

**NEVER do any of these:**
- ❌ `kill`, `pkill`, `killall` - NEVER manually kill processes
- ❌ `uvicorn`, `python -m uvicorn` - NEVER start server directly  
- ❌ `pytest` without `make test` - NEVER run tests directly
- ❌ `lsof -i :8000` then kill - NEVER manage ports manually
- ❌ `python`, `python3` - NEVER execute Python directly

**ALWAYS use these Makefile commands:**

| Task | Command | Notes |
|------|---------|-------|
| Start server | `make serve &` | Auto-stops existing, handles port cleanup |
| Stop server | `make stop` | Stops any running server on port |
| Run ALL tests | `make test` | Auto-stops server first, runs full suite |
| Run specific tests | `uv run pytest tests/path -v` | For targeted testing only |
| Check translations | `make check-i18n` | Find missing or inconsistent translations |
| Format/lint | `make format` | Auto-fixes linting issues |
| Reset database | `make seed` | Drops, migrates, seeds |
| Coverage report | `make coverage` | Full coverage analysis |

### Why This Matters

`make serve` automatically:
- Runs `make stop` first (kills any existing process on port)
- Starts fresh server with latest code
- Uses `uv run` for isolated environment
- Starts ngrok tunnel if needed
- Runs in background (`&`) so terminal remains usable

`make test` automatically:
- Runs `make stop` first (ensures server is not running)
- Runs all test suites (unit, contract, integration)
- Reports failures properly

**For running scripts and code snippets:**
- ✅ **Preferred**: Use Pylance MCP for Python code snippets (avoids shell quoting issues)
- ✅ `uv run python scripts/script.py` for standalone scripts
- ✅ `uv run ruff check .` for linting

**CRITICAL: Environment-specific database targets:**
- `make seed` and `make db-reset` are **BLOCKED** in `ENV=prod` (safety mechanism)
- Production uses `make backup` and `make restore` for data management
- Dev mode: application **must be offline** during `seed` or `db-reset`
- Verify environment with `grep '^ENV=' .env` before running database commands

## Commands Reference

```bash
make serve &  # Start server (MANDATORY for testing code changes)
make test     # Run all tests (MANDATORY before committing)
make seed     # Reset database + run migrations + seed data (dev only, app offline)
make format   # Run ruff linter with auto-fix
make coverage # Full coverage report
make check-i18n # Validate translation completeness (Python/JS/HTML vs translations.json)
make backup   # Create timestamped backup (prod only, creates backups/sosenki-YYYYMMDD-HHMMSS.db)
make restore  # Restore from latest backup (prod only, use BACKUP=path to specify)
```

## Environment Configuration

**Two modes controlled by `.env`:**
- `ENV=dev` — Local development (uses `sosenki.dev.db`, allows `seed`/`db-reset`)
- `ENV=prod` — Production (uses `sosenki.db`, requires `backup`/`restore` for data management)

**Development modes for `ENV=dev`:**
1. **Local (ngrok)** — Default, auto-starts ngrok tunnel for external Telegram webhooks
   - No DOMAIN needed, `make serve` manages tunnel automatically
   - Creates `/tmp/.sosenki-env` with dynamic `WEBHOOK_URL` and `MINI_APP_URL`

2. **LAN** — Set `DOMAIN=192.168.x.x` for testing on local network
   - Uses `http://$DOMAIN:$PORT` (no ngrok), useful for device testing
   - `scripts/setup-environment.sh` detects DOMAIN presence and skips ngrok

**Production setup:**
- Set `DOMAIN=yourdomain.com` in `.env`
- `make install` derives `WEBHOOK_URL` and `MINI_APP_URL` automatically
- Configures Caddy (reverse proxy with auto-SSL) + systemd service
- Requires port forwarding: external 80/443 → internal 80/443

## Key Patterns & Integration Points

### 1. Authentication Flow (`src/services/auth_service.py`)

**Telegram Mini App authentication:**
- Extract init_data from `Authorization: tma <data>` header or `x-telegram-init-data` header
- Verify signature using bot token + HMAC-SHA256
- Extract `telegram_id` from validated init_data
- Resolve to `AuthorizedUser` context (authenticated user + target user + admin flags)

**Admin context switching:**
- Admins can access any user's data via `target_telegram_id` in request body
- `AuthorizedUser.switched_context` flag indicates admin override
- `authorize_account_access()` helper checks owner/staff permissions with admin bypass

### 2. MCP Server + LLM Integration

**FastMCP tools (src/api/mcp_server.py):**
- `get_balance(user_id)` — User's current balance
- `list_bills(user_id, limit)` — Recent bills with status
- `get_period_info(period_id)` — Service period details
- `create_service_period(name, start_date, end_date)` — Admin-only period creation

**Ollama service (src/services/llm_service.py):**
- `/ask` command uses Ollama for tool-calling
- `get_user_tools()` returns read-only tools (balance, bills, period info)
- `get_admin_tools()` adds write tools (create_service_period)
- `execute_tool()` routes to corresponding service methods
- Role-based filtering prevents non-admins from accessing write tools

**Tool execution pattern:**
```python
# In bot handler
from src.services.llm_service import OllamaService, ToolContext

ctx = ToolContext(user_id=user.id, is_admin=user.is_administrator, session=session)
ollama = OllamaService(model="qwen2.5:1.5b")
response = await ollama.chat(query, tools=get_admin_tools() if is_admin else get_user_tools(), ctx=ctx)
```

### 3. Internationalization (i18n)

**Single source of truth:** `src/static/mini_app/translations.json`

**Flat key convention with prefixes:**
- `btn_*` — Clickable buttons (`btn_approve`, `btn_cancel`)
- `msg_*` — Informational messages/notifications (`msg_welcome`, `msg_period_created`)
- `err_*` — Error messages (`err_invalid_number`, `err_not_authorized`)
- `prompt_*` — Input prompts for bot conversations (`prompt_meter_start`, `prompt_budget_main`)
- `status_*` — State labels (`status_open`, `status_closed`, `status_pending`)
- `empty_*` — Empty state messages (`empty_bills`, `empty_transactions`)
- `nav_*` — Navigation labels (`nav_balance`, `nav_invest`)

**Usage patterns:**
```python
# Python
from src.services.localizer import t
message = t("msg_welcome")
message = t("err_group_chat", bot_name="SOSenkiBot")  # with placeholder
```
```javascript
// JavaScript (app.js loads translations)
t("btn_approve")
```
```html
<!-- HTML data attribute -->
<span data-i18n="btn_open_app"></span>
```

**Validation:** `make check-i18n` finds missing/unused keys by scanning Python, JS, and HTML files.

### 4. Helper Functions & Utilities

**Locale & Formatting (`src/services/locale_service.py`):**
- `format_currency(amount)` — Russian currency formatting with spaces (e.g., "100 000 ₽")
- `format_local_datetime(dt)` — Locale-aware datetime formatting
- `get_currency_symbol()` — Current locale currency symbol

**Parsing (`src/utils/parsers.py`):**
- `parse_russian_decimal(text)` — Parse Russian number format to Decimal
- `parse_russian_currency(text)` — Parse currency strings to Decimal

**Usage Pattern:**
```python
from src.services.locale_service import format_currency
from src.utils.parsers import parse_russian_decimal

# Always use helpers for consistent formatting
amount_display = format_currency(transaction.amount)  # "85 000 ₽"
user_input = parse_russian_decimal("85 000,50")       # Decimal('85000.50')
```

**Critical:** Before implementing custom parsing/formatting:
1. Check if helper already exists in `locale_service.py` or `parsers.py`
2. Use existing helpers for consistency across the application
3. Only create new helpers if functionality doesn't exist

### 5. Database Schema & Migrations

**Production migration workflow:**
- Alembic migrations in `alembic/versions/` using standard workflow
- Generate: `uv run alembic revision --autogenerate -m "description"`
- Apply: `uv run alembic upgrade head`
- Check status: `uv run alembic current`
- After schema changes: verify with `uv run alembic upgrade head && make seed` (dev only)

**Role-based access (src/models/user.py):**
- `is_active` — Primary gate for Mini App access
- `is_administrator` — Can approve/reject access requests + admin tools
- `is_owner` — Property owner
- `is_stakeholder` — Legal contract signed (only valid when `is_owner=True`)
- `is_investor` — Can access Invest features (requires `is_active=True`)
- `is_tenant` — Has rental contract

Users can have multiple roles simultaneously via independent boolean flags.

### 6. Testing Strategy

**Test database isolation:**
- Tests use `test_sosenki.db` (configured in `tests/conftest.py`)
- Fresh schema applied via Alembic migrations before each test run
- `tests/conftest.py` runs `alembic upgrade head` automatically on import
- Dev database: `sosenki.dev.db`, Production: `sosenki.db`
- **Seeding tests** (`seeding/tests/`) use production database (`sosenki.db`) for data integrity validation

**Contract tests (`tests/contract/`):**
- API endpoint schemas (Pydantic model validation)
- MCP tool registration + parameter schemas
- Response structure validation
- Bot handler registration (verify handlers are properly attached)

**Integration tests (`tests/integration/`):**
- End-to-end workflows (request approval, period creation)
- Multi-step bot interactions
- Database state verification

**Unit tests (`tests/unit/`):**
- Service layer logic (balance calculation, period validation)
- Utility functions (localizer, parsers)
- MCP tool coverage (error handling, date validation)

**Test markers (use with `-m`):**
- `@pytest.mark.contract` — API/schema tests
- `@pytest.mark.integration` — Full workflow tests
- `@pytest.mark.unit` — Isolated logic tests

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
- Use standard Alembic migration workflow: `alembic revision --autogenerate -m "description"`
- After schema changes, verify with `uv run alembic upgrade head && make seed`
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
- [ ] Migration generated via `alembic revision --autogenerate` if schema changed
- [ ] Developer ran `uv run alembic upgrade head && make seed` and verified success
- [ ] Tests pass: `make test` shows all green
- [ ] No secrets or hard-coded paths in diff
- [ ] Context7 documentation verified for all new dependencies
- [ ] i18n keys added to `translations.json` if user-facing text changed

## Known Patterns & TODOs

**Security improvements needed (from Makefile):**
- auth_date expiration check (±5min) — replay attack mitigation
- Use `hmac.compare_digest()` — timing attack prevention
- Rate limiting (slowapi) — DoS/brute force protection
- CORS `allow_credentials=False` — credential leak prevention

**Planned features (from Makefile):**
- Electricity reading handler
- Notification system from Telegram
- Invest tracking module
- Rules/Job descriptions module

**MCP server optimization:**
- Tool confirmation prompts for write operations
- Enhanced error messages with recovery suggestions

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
