# Quickstart: Welcome Mini App Development

**Feature**: 002-welcome-mini-app
**Date**: 2025-11-05
**Target Audience**: Developers implementing this feature

## Quick Overview

This feature adds a Telegram Mini App that approved users can access after their request is approved by an administrator. The Mini App verifies user approval status and displays a welcome message + navigation menu for approved users, or an access denied message for non-approved users. **YAGNI Applied**: Welcome notification sent via 001-request-approval webhook; `is_active` is primary access gate; feature-level access via `is_investor` flag (Invest features); optional analytics via MiniAppSession.

## Prerequisites

- Python 3.11+ installed
- SOSenki repository cloned
- `uv` package manager installed (see `.specify/memory/constitution.md`)
- Telegram bot token and mini app ID (from BotFather)

## Local Development Setup

### 1. Install Dependencies

```bash
cd path/to/SOSenki
uv sync --all-groups
```

This installs all dependencies including dev tools (pytest, etc.) and creates `.venv`.

### 2. Create Environment Variables

Create a `.env` file in the project root (never commit to git):

```env
# Existing from 001-request-approval
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_TELEGRAM_ID=your_admin_id_here
DATABASE_URL=sqlite:///sosenki.db

# New for 002-welcome-mini-app
TELEGRAM_MINI_APP_ID=your_mini_app_id_here
MINI_APP_URL=https://localhost:8000/mini-app
```

### 3. Run Database Migrations

```bash
cd path/to/SOSenki
uv run alembic upgrade head
```

This applies all migrations including:
- New unified User table with boolean role flags (is_investor, is_administrator, is_owner, is_staff)
- `is_active` = PRIMARY Mini App access gate
- Rename client_requests → access_requests (audit log)
- Optional: MiniAppSession table (for analytics, can be deferred)

### 4. Start the Development Server

```bash
cd path/to/SOSenki
uv run python src/main.py
```

Server runs on `http://localhost:8000`

Endpoints:
- Health check: `GET http://localhost:8000/health`
- Mini App: `GET http://localhost:8000/mini-app`
- API: `GET http://localhost:8000/api/mini-app/init`

## Project Structure for This Feature

### New Files/Directories (Refactored)

```
src/
├── api/
│   ├── mini_app.py              # Mini App API endpoints
│   └── approval.py              # Approval notification endpoint
├── services/
│   ├── approval_service.py      # Approval notification logic
│   ├── user_service.py          # User management (NEW unified model)
│   ├── access_request_service.py # Was request_service.py (renamed)
│   └── mini_app_service.py      # Mini App state management
├── models/
│   ├── user.py                  # NEW unified User model (replaces separate Admin/Client)
│   ├── access_request.py        # NEW (renamed from client_request.py)
│   └── admin_config.py          # Existing (logic moves to user.py)
├── bot/
│   └── approval_handlers.py     # NEW: Approval response handling
└── static/
    └── mini_app/
        ├── index.html           # Mini App UI
        ├── styles.css           # Nature-inspired styling
        └── app.js               # Client-side logic

migrations/
└── versions/
    └── [timestamp]_refactor_user_model_and_add_mini_app_schema.py

specs/002-welcome-mini-app/
├── data-model.md                # Phase 1: Database schema
├── research.md                  # Phase 0: Technical decisions
├── contracts/
│   └── mini-app-api.md         # API specification
├── checklists/
│   └── requirements.md         # Spec validation
└── tasks.md                    # Phase 2: Implementation tasks (TBD)
```

### Key Architectural Changes

**YAGNI Applied**: 
- `is_active` = PRIMARY Mini App access gate for ALL users (True = can access Mini App)
- `is_investor` = Feature-level flag (can access Invest features, requires is_active=True)
- User model uses independent boolean flags allowing simultaneous multiple roles
- **No ApprovalNotification table** - welcome sent via 001-request-approval webhook
- **No redundant timestamps** - use responded_at instead of approved_at; mini_app_first_opened_at not needed
- **Optional MiniAppSession** - analytics can be deferred if not needed

```
src/
├── bot/handlers.py             # Add approval response handler
├── models/client_request.py    # Extend with registration fields
└── main.py                     # Mount mini app static files route

migrations/
└── versions/
    └── [timestamp]_add_welcome_mini_app_schema.py
```

## Development Workflow

### 1. Write Tests First (TDD)

```bash
# Contract test for Mini App initialization
cd path/to/SOSenki
uv run pytest tests/contract/test_mini_app_endpoints.py -v

# Integration test for full flow
uv run pytest tests/integration/test_mini_app_flow.py -v

# Unit test for registration service
uv run pytest tests/unit/test_registration_service.py -v
```

### 2. Implement Feature

Follow this order:

**Phase A: Database**
- Create Alembic migration file
- Define User (with is_client, is_administrator, is_owner, is_staff flags), AccessRequest tables
- Optional: MiniAppSession table (skip if analytics deferred)
- Run migration: `uv run alembic upgrade head`

**Phase B: Backend Services**
- Implement `user_service.can_access_mini_app(telegram_id)` (checks user.is_active=True)
- Implement `user_service.can_access_invest(telegram_id)` (checks user.is_investor=True)
- Implement `mini_app_service.get_user_profile(telegram_id)` (returns approved user data)

**Phase C: API Endpoints**
- Implement `GET /api/mini-app/init` (handles Telegram signature verification)
- Implement `GET /api/mini-app/verify-registration` (refresh check)
- Implement `POST /api/mini-app/menu-action` (placeholder)

**Phase D: Frontend**
- Create `src/static/mini_app/index.html` (structure)
- Create `src/static/mini_app/styles.css` (nature-inspired colors)
- Create `src/static/mini_app/app.js` (client logic)

**Phase E: Integration**
- Wire approval handler to send notification
- Test full flow: approval → notification → mini app open

### 3. Run All Tests

```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

Target: >80% code coverage

### 4. Manual Testing

#### Test Approval Workflow

```bash
# 1. Send /request as non-admin user
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{"message": "Please give me access to SOSenki"}'

# 2. As admin, approve the request (via Telegram bot interface or API)

# 3. Check that User was created with is_active=True
sqlite3 sosenki.db "SELECT telegram_id, is_active, is_investor, is_administrator FROM user WHERE telegram_id='USER_ID'"

# 4. Open Mini App and verify it loads
curl -X GET http://localhost:8000/api/mini-app/init \
  -H "X-Telegram-Init-Data: $(get_init_data_from_telegram)"
```

#### Test Registration Check

```bash
# Non-registered user
curl -X GET http://localhost:8000/api/mini-app/verify-registration \
  -H "X-Telegram-Init-Data: non_registered_user_init_data"

# Response should be { "isRegistered": false, ... }
```

#### Test UI in Telegram Sandbox

1. Open Telegram
2. Find @sosenkibot (or your dev bot)
3. Click "Open App" button in Mini App (or send `/start` to open)
4. Verify:
   - Registered users see welcome + 3 menu items (Rule, Pay, Invest)
   - Non-registered users see "Access is limited" message
   - Colors are nature-inspired (pine, water, sand)
   - Layout is minimalistic and clean

## Key Files to Understand

| File | Purpose |
|------|---------|
| `src/api/mini_app.py` | FastAPI route handlers for Mini App endpoints |
| `src/services/user_service.py` | User queries and approval checks |
| `src/models/user.py` | SQLAlchemy model for unified User (boolean role flags) |
| `src/models/access_request.py` | SQLAlchemy model for AccessRequest (audit log) |
| `src/static/mini_app/index.html` | Mini App UI structure |
| `src/static/mini_app/styles.css` | Nature-inspired color palette + layout |
| `src/static/mini_app/app.js` | Client-side Telegram WebApp integration |
| `specs/002-welcome-mini-app/data-model.md` | Database schema reference |
| `specs/002-welcome-mini-app/contracts/mini-app-api.md` | API endpoint specifications |

## Configuration Reference

### Environment Variables

| Variable | Type | Example | Purpose |
|----------|------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | string | `123:ABC_xyz` | Bot authentication |
| `ADMIN_TELEGRAM_ID` | int | `123456789` | Admin user for approvals |
| `TELEGRAM_MINI_APP_ID` | string | `my_mini_app` | Mini App identifier |
| `MINI_APP_URL` | string | `https://example.com/mini-app` | Deeplink base URL |
| `DATABASE_URL` | string | `sqlite:///sosenki.db` | SQLite connection string |

### Constants (in code)

```python
# Caching
REGISTRATION_CACHE_TTL = 300  # 5 minutes in browser

# Performance targets
INIT_LOAD_TARGET = 3.0  # seconds
REGISTRATION_QUERY_TARGET = 0.1  # seconds

# Colors
COLOR_PINE = "#2D5016"
COLOR_WATER = "#0099CC"
COLOR_SAND = "#D4A574"

# Telegram signature verification
TELEGRAM_SIGNATURE_TOLERANCE = 300  # ±5 minutes
```

## Common Tasks

### Add a New Menu Item

**Note**: Menu items (Rule, Pay, Invest) are stubs for MVP. To extend:

1. Update `src/static/mini_app/index.html` menu structure
2. Add handling in `src/static/mini_app/app.js` click handler
3. Create new service/endpoint for the feature
4. Add tests

### Debug Registration Status

```python
# In Python shell
from src.services.registration_service import is_user_registered
result = is_user_registered("123456789")
print(result)  # True or False
```

### View Database Schema

```bash
sqlite3 sosenki.db ".schema"
```

### Reset Local Database

```bash
rm sosenki.db
uv run alembic upgrade head
```

## Troubleshooting

### "Invalid Telegram signature"

- Ensure `X-Telegram-Init-Data` header is being sent correctly
- Verify `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Check that Telegram signature validation is not off in development



### "No such table: user" or "No such table: access_request"

- Migrations haven't been applied
- Run: `uv run alembic upgrade head`
- Verify: `sqlite3 sosenki.db "SELECT * FROM user LIMIT 1"`

### Mini App loads but shows "Access is limited" unexpectedly

- Check that User record exists with is_active=True: `sqlite3 sosenki.db "SELECT telegram_id, is_active FROM user WHERE telegram_id='USER_ID'"`
- Verify user was actually approved (AccessRequest.status='approved' AND responded_at is set)
- Check user_service.can_access_mini_app() logic

### CORS or origin errors


- Mini App is expected to run within Telegram client context
- Development deeplink format: `https://t.me/[BOT_NAME]/[APP_ID]?startapp=dev`
- Ensure backend `X-Telegram-Init-Data` header validation is in place

## Next Steps

1. Review and approve `data-model.md` and `contracts/mini-app-api.md`
2. Create implementation tasks using `/speckit.tasks` command
3. Implement features in this order: database → backend → API → frontend
4. Run tests continuously during development
5. Manual testing in Telegram sandbox before deployment

## References

- Telegram Mini App API Docs: https://core.telegram.org/bots/webapps
- FastAPI Docs: https://fastapi.tiangolo.com/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/
- Project Constitution: `.specify/memory/constitution.md`
- Feature Specification: `specs/002-welcome-mini-app/spec.md`
