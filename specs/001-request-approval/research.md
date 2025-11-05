# Phase 0 Research: Client Request Approval Workflow

**Research Date**: 2025-11-04  
**Feature**: Client Request Approval Workflow (001-request-approval)  
**Status**: Complete

## Research Findings

### 1. Telegram Bot Async Webhooks with python-telegram-bot

**Question**: What are best practices for implementing async webhook handlers with `python-telegram-bot`?

**Decision**: Use `python-telegram-bot` (PTB) version 13+ with async dispatcher and webhook mode for production deployment.

**Rationale**:

- PTB v13+ fully supports `asyncio`-based update handling (essential for FastAPI integration)
- Webhook mode is production-recommended over polling (reduces latency, resource usage)
- PTB provides built-in handler patterns that map Telegram updates to async coroutines
- Well-documented async examples in official repository

**Alternatives Considered**:

- **aiogram** (async-first Telegram library): Lighter weight, but PTB has larger community and better FastAPI integration examples
- **Polling mode**: Simpler to start but inefficient for production; violates KISS principle with added infrastructure

**Best Practices**:

- Register handlers as async functions: `@app.message_handler(commands=['request'])`
- Use PTB's `Application` class (v20+) for modern async setup
- Webhook endpoint receives Telegram updates as JSON via HTTP POST
- Bot.send_message() is already async-compatible

**Dependencies**:

- `python-telegram-bot[all]` (includes aiohttp for async requests)
- Version: 20.0+ (latest stable with full async support)

---

### 2. FastAPI Webhook Endpoint Integration

**Question**: How to integrate Telegram webhook endpoint with FastAPI?

**Decision**: Implement FastAPI POST endpoint at `/webhook/telegram` that receives raw Telegram updates and dispatches to PTB handlers.

**Rationale**:

- FastAPI handles HTTP routing and body parsing (Telegram sends JSON)
- FastAPI's async support aligns with PTB's async handlers
- Automatic OpenAPI documentation
- Pydantic validation of incoming Telegram Update objects

**Alternatives Considered**:

- Flask + python-telegram-bot: Works but less async-friendly
- Bare ASGI server: More overhead than FastAPI for this use case

**Best Practices**:

- Accept `Update` object from Telegram (PTB provides Pydantic model)
- Return HTTP 200 immediately (Telegram doesn't care about response body)
- Delegate message processing to background tasks or queue (if latency-sensitive)
- For MVP: Synchronous response is acceptable (sub-second processing per spec)

**Implementation Pattern**:

```python
@app.post("/webhook/telegram")
async def telegram_webhook(update: Update):
    await application.process_update(update)
    return {"ok": True}
```

**Dependencies**:

- `fastapi`
- `uvicorn` (ASGI server)
- `pydantic` (already in FastAPI)

---

### 3. SQLAlchemy + Alembic for Request Persistence

**Question**: How to structure database schema and migrations for simple request tracking?

**Decision**: Use SQLAlchemy ORM for `ClientRequest` model with Alembic for version-controlled migrations.

**Rationale**:

- SQLAlchemy is OSenki project standard per constitution (used with FastAPI + SQLite)
- Alembic provides reproducible schema evolution (required for dev/prod consistency)
- Simple schema (ClientRequest, Administrator config) benefits from ORM mapping
- Both tools work seamlessly with SQLite in dev and PostgreSQL in production

**Schema Design**:

- **ClientRequest** table:
  - `id` (INT, PK)
  - `client_telegram_id` (STRING, unique constraint for pending requests)
  - `request_message` (TEXT)
  - `submitted_at` (DATETIME)
  - `status` (ENUM: pending, approved, rejected)
  - `admin_response` (TEXT, nullable)
  - `responded_at` (DATETIME, nullable)
  - `created_at` (DATETIME, auto)
  - `updated_at` (DATETIME, auto)

- **AdminConfig** table (singleton):
  - `admin_telegram_id` (STRING, primary value from environment)
  - `config_key` (STRING, PK)
  - `config_value` (TEXT)
  - `updated_at` (DATETIME)

**Alternatives Considered**:

- Direct SQL queries: Violates DRY principle, harder to maintain
- NoSQL (MongoDB): Overkill for simple request tracking, adds external dependency
- Plain SQLite without ORM: More code, less type safety

**Best Practices**:

- Use Alembic `init` to create `alembic/` directory with version tracking
- Auto-generate migrations from model changes: `alembic revision --autogenerate -m "reason"`
- Store Alembic config in `alembic.ini` at repository root
- Always keep `alembic/versions/` committed (complete schema history)
- Constraint: Never drop `client_telegram_id` column; prevent orphaned requests

**Dependencies**:

- `sqlalchemy[asyncio]` (async support for FastAPI)
- `alembic` (migration tool)
- `psycopg2-binary` or `aiosqlite` (adapter for PostgreSQL or SQLite; depends on environment)

---

### 4. Pytest Fixtures for Telegram Bot Testing

**Question**: How to structure unit/integration tests for Telegram bot handlers without hitting live Telegram API?

**Decision**: Use pytest fixtures to mock `Application` instance, `Update` objects, and `Bot` send methods.

**Rationale**:

- `python-telegram-bot` provides `telegram.Update` and `telegram.Message` classes that are easily instantiable
- Mock fixtures prevent external API calls and ensure fast, deterministic tests
- Pytest fixtures enable reuse across contract, integration, and unit tests
- Matches project's test-first approach (TDD)

**Test Structure**:

- **Contract tests** (`tests/contract/`): Verify webhook endpoint accepts POST requests with valid Telegram Update payloads, returns HTTP 200
- **Integration tests** (`tests/integration/`): Mock bot/DB, test full flows (client request → admin notification → approval → client welcome)
- **Unit tests** (`tests/unit/`): Test individual services (request_service, notification_service, admin_service) in isolation

**Fixture Pattern**:

```python
@pytest.fixture
def mock_bot(mocker):
    bot = mocker.MagicMock()
    bot.send_message = mocker.AsyncMock(return_value=None)
    return bot

@pytest.fixture
def sample_telegram_update():
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=123456789, type="private"),
            text="/request",
            from_user=User(id=123456789, first_name="TestUser", is_bot=False)
        )
    )
```

**Alternatives Considered**:

- Integration tests against staging Telegram bot: Slow, flaky, violates KISS
- Manual testing only: No repeatability, violates test-first principle

**Best Practices**:

- Use `pytest-asyncio` for async test functions
- Use `pytest-mock` for mocking (better ergonomics than unittest.mock)
- Fixtures should be in `tests/conftest.py` for reuse
- Test both happy path and edge cases (invalid input, DB errors, bot failures)

**Dependencies**:

- `pytest`
- `pytest-asyncio`
- `pytest-mock`

---

### 5. Environment Configuration & Secrets Management

**Question**: How to safely manage bot token and admin Telegram ID without hardcoding?

**Decision**: Load from environment variables; provide `.env.example` template for local development.

**Rationale**:

- Follows project constitution (no hard-coded secrets)
- Python-dotenv or FastAPI dependency injection both work; choose dotenv for simplicity
- `.env` loaded at startup, not committed to repo (.gitignore)
- Production uses environment variables directly (no .env file)

**Configuration Pattern**:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # For local dev

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
```

**Alternatives Considered**:

- Pydantic Settings: More powerful but heavier for MVP
- Config file (JSON/YAML): Adds file complexity, still needs secret injection

**Best Practices**:

- Validate env vars at startup (error if missing)
- Provide `.env.example` with dummy values
- Never log secrets
- Rotate bot token if exposed

**Dependencies**:

- `python-dotenv` (convenience for local dev)
- `os` (stdlib, for production)

---

## Summary: Ready for Phase 1 Design

All research questions resolved. Key findings:

✅ **Telegram Integration**: Use `python-telegram-bot` v20+ with async webhooks  
✅ **HTTP Framework**: FastAPI webhook endpoint `/webhook/telegram`  
✅ **Database**: SQLAlchemy ORM + Alembic migrations  
✅ **Testing**: pytest fixtures + mocking (no live API calls)  
✅ **Configuration**: Environment variables + .env.example  

**No blockers identified.** Architecture is aligned with project constitution (YAGNI, KISS, DRY, tech stack). Ready to proceed to Phase 1.

**Next**: Generate `data-model.md`, API contracts, and `quickstart.md`.
