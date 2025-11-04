# Quickstart Guide: Client Request Approval Workflow

**Feature**: Client Request Approval Workflow (001-request-approval)  
**Date**: 2025-11-04  
**Target Audience**: Developers implementing this feature locally

## Prerequisites

- Python 3.11+
- uv package manager (<https://docs.astral.sh/uv/>)
- A Telegram account
- A Telegram bot created via @BotFather

## Local Development Setup

### 1. Clone and Setup Environment

```bash
# Create .env file for local development (copy template)
cp .env.example .env

# Edit .env with your values:
# - TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
# - ADMIN_TELEGRAM_ID=<your-telegram-id>
# - DATABASE_URL=sqlite:///./sosenkibot.db (default, local SQLite)
# - WEBHOOK_URL=https://your-domain.com/webhook/telegram (for production)
```

### 2. Install Dependencies

```bash
# Install all dependencies including dev/test dependencies
uv sync

# Verify installation
uv run python --version  # Should be 3.11+
```

### 3. Initialize Database

```bash
# Create initial migration (should already exist)
uv run alembic upgrade head

# Verify tables exist
uv run python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('sqlite:///./sosenkibot.db')
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"
```

### 4. Run Tests

```bash
# Run all tests (contract, integration, unit)
uv run pytest -v

# Run specific test file
uv run pytest tests/contract/test_request_endpoint.py -v

# Run with coverage
uv run pytest --cov=src tests/
```

### 5. Start Bot Locally (Development Mode)

#### Option A: Polling Mode (Easy, Development Only)

```bash
# Bot will poll Telegram for updates (not webhook-based)
uv run python -m src.main --polling

# Bot will be ready for testing in Telegram
# Send /request to @yourbotname
```

#### Option B: Webhook Mode (Production-like, Requires ngrok)

```bash
# In one terminal, start ngrok tunnel
ngrok http 8000

# In another terminal, update WEBHOOK_URL in .env
# WEBHOOK_URL=https://your-ngrok-url.ngrok.io/webhook/telegram

# Start bot with webhook
uv run python -m src.main --webhook
```

## Testing the Feature

### Manual Testing (Telegram)

1. **Test Client Request**:
   - Open Telegram and find your bot (@yourbotname)
   - Send: `/request Please give me access to SOSenki`
   - Expected: You receive confirmation "Your request has been received and is pending review"

2. **Test Admin Approval**:
   - Using admin account, you should receive notification from bot
   - Reply with: `Approve`
   - Expected (as client): Welcome message with access granted
   - Expected (as admin): Confirmation "Request approved and client notified"

3. **Test Admin Rejection**:
   - Send another `/request`
   - Using admin account, reply to notification with: `Reject`
   - Expected (as client): Rejection message
   - Expected (as admin): Confirmation "Request rejected and client notified"

### Automated Testing

```bash
# Run all tests
uv run pytest -v

# Run with specific marker
uv run pytest -m integration -v  # Only integration tests
uv run pytest -m contract -v     # Only contract tests

# Run specific test
uv run pytest tests/integration/test_client_request_flow.py::test_client_submits_request -v
```

## Troubleshooting

```bash
# Example troubleshooting command
```

- Double-check TELEGRAM_BOT_TOKEN in .env

- Get your Telegram ID: Send `/start` to @userinfobot

- Kill any running bot processes

- Send `/start` to your bot to refresh command list

## Code Structure Overview

```text
src/
├── models/
│   ├── client_request.py       # SQLAlchemy ORM model for ClientRequest
│   └── admin_config.py         # Admin configuration and loading
├── services/
│   ├── request_service.py      # Business logic for request management
│   ├── notification_service.py # Telegram message sending
│   └── admin_service.py        # Admin approval/rejection logic
├── bot/
│   ├── handlers.py             # Telegram command handlers (/request, Approve, Reject)
│   └── config.py               # Bot token, admin ID from environment
├── api/
│   └── webhook.py              # FastAPI webhook endpoint
├── migrations/                 # Alembic database migrations
└── main.py                     # Application entry point
```

## Common Development Tasks

### Add a New Dependency

```bash
# Add package via uv
uv add package-name

# Or with extras:
uv add package[extra1,extra2]

# Update pyproject.toml and uv.lock automatically

# Verify with MCP Context7 documentation before committing
# (per project constitution)
```

### Run Database Migrations

```bash
# Create new migration after model change
uv run alembic revision --autogenerate -m "Add new field to ClientRequest"

# Apply migrations
uv run alembic upgrade head

# View migration history
uv run alembic history
```

### Debug Bot Locally

```bash
# Run with verbose logging
uv run python -m src.main --logging DEBUG

# Or directly in Python
uv run python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.main import app
# ... start debugging
"
```

### Clear Local Database

```bash
# Delete and recreate
rm sosenkibot.db

# Re-initialize
uv run alembic upgrade head
```

## Environment Variables Reference

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| TELEGRAM_BOT_TOKEN | Yes | 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 | Bot token from @BotFather |
| ADMIN_TELEGRAM_ID | Yes | 987654321 | Your Telegram ID (for admin approval) |
| DATABASE_URL | No | sqlite:///./sosenkibot.db | Database connection string |
| WEBHOOK_URL | No (polling) | <https://example.com/webhook/telegram> | Webhook URL for production |
| DEBUG | No | true | Enable debug logging |

## Common Issues & Solutions

**Problem**: "Bot token invalid" error

**Solution**:

- Double-check TELEGRAM_BOT_TOKEN in .env
- Verify token doesn't have spaces
- Regenerate token from @BotFather if needed

---

**Problem**: "Admin Telegram ID not found"

**Solution**:

- Get your Telegram ID: Send `/start` to @userinfobot
- Update ADMIN_TELEGRAM_ID in .env
- Restart bot

---

**Problem**: Tests fail with "Database locked"

**Solution**:

- Kill any running bot processes
- Delete `sosenkibot.db`
- Re-run: `uv run alembic upgrade head`
- Re-run tests: `uv run pytest -v`

---

**Problem**: `/request` command not recognized

**Solution**:

- Send `/start` to your bot to refresh command list
- Wait 30 seconds for Telegram to sync
- Try `/request` again
- If still failing, check server logs with DEBUG=true

---

## Next Steps

1. **For Developers**: Implement handlers in `src/bot/handlers.py` and services in `src/services/`
2. **For Testers**: Write additional integration tests in `tests/integration/`
3. **For Deployment**: See main repository docs on deployment to production server with webhooks
4. **For Features**: Additional workflows (bulk approval, expiration, etc.) go to Phase 2

---

**Questions?**: Refer to feature spec (`spec.md`) or implementation plan (`plan.md`).
