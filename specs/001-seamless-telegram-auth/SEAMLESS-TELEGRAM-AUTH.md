# 001-seamless-telegram-auth — Feature Guide

## Overview

The "Seamless Telegram Auth" feature implements an MVP flow for Telegram user onboarding and admin approval via the SOSenki ecosystem. Users open the Mini App, verify their Telegram identity, and submit join requests. Administrators review and approve/reject requests from an admin dashboard.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for local development)
- Telegram Bot (for webhook/polling setup, optional for MVP)
- Environment variables configured (see `.env.example`)

### Local Development Setup

1. **Install dependencies**

   ```bash
   cd backend
   uv sync
   ```

2. **Set up database**

   ```bash
   # Run migrations
   uv run alembic upgrade head
   ```

3. **Run the application**

   ```bash
   cd backend
   uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Run tests**

   ```bash
   # All tests
   uv run pytest backend/tests/

   # Unit tests only
   uv run pytest backend/tests/unit/

   # Contract tests only
   uv run pytest backend/tests/contract/

   # Integration tests only
   uv run pytest backend/tests/integration/
   ```

## Feature Flows

### Flow 1: Linked User Welcome (US1)

**Endpoint**: `POST /miniapp/auth`

**Scenario**: User opens Mini App, already has a linked SOSenkiUser account

1. Frontend calls `/miniapp/auth` with `init_data` (Telegram WebApp data)
2. Backend verifies `init_data` signature and timestamp
3. Backend queries `SOSenkiUser` by `telegram_id` from initData
4. Response: `{ "linked": true, "user": { ... }, "request_form": null }`
5. Frontend shows welcome/home page

**Test**: `backend/tests/integration/test_miniapp_auth.py`

### Flow 2: Unlinked User Request Form (US2)

**Endpoint**: `POST /miniapp/auth` (continuation)

**Scenario**: User opens Mini App, no linked account → shows request form

1. Frontend calls `/miniapp/auth` with `init_data`
2. Backend verifies initData and queries for linked user
3. No user found → Response: `{ "linked": false, "user": null, "request_form": { "telegram_id": ..., "first_name": ..., "note": ... } }`
4. Frontend shows join request form to user
5. User submits form via `POST /requests`

**Endpoint**: `POST /requests`

**Request body**:

```json
{
  "telegram_id": 123456789,
  "telegram_username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "email": "john@example.com",
  "note": "Interested in co-living spaces"
}
```

**Response**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "telegram_username": "john_doe",
  "first_name": "John",
  "status": "pending",
  "created_at": "2025-11-03T21:00:00Z"
}
```

**Tests**: `backend/tests/integration/test_create_request_flow.py`

### Flow 3: Admin Review & Action (US3)

**Endpoints**:

- `GET /admin/requests` — List all pending requests
- `POST /admin/requests/{request_id}/action` — Accept or reject

**Scenario**: Admin reviews pending requests and accepts/rejects

1. Admin calls `GET /admin/requests` to see pending TelegramUserCandidates
2. Admin reviews request details (name, username, note, etc.)
3. Admin sends `POST /admin/requests/{id}/action` with action and admin_id

**Accept Request**:

```json
{
  "action": "accept",
  "admin_id": 1
}
```

**Response**: `200 OK`

```json
{
  "request_id": 1,
  "action": "accept",
  "user_id": "..."
}
```

**Side Effects**:

- New `SOSenkiUser` created with `telegram_id` and role `["user"]`
- `AdminAction` audit record created
- Telegram user notified: "✅ Your access request has been approved!"
- Request status updated to `"accepted"`

**Reject Request**:

```json
{
  "action": "reject",
  "admin_id": 1,
  "reason": "Please try again later"
}
```

**Response**: `200 OK`

**Side Effects**:

- Telegram user notified: "❌ Your access request has been declined. Reason: Please try again later"
- Request status updated to `"rejected"`
- No `SOSenkiUser` created

**Duplicate Handling**: If a user with the same `telegram_id` already exists, accepting the request returns `409 Conflict`.

**Tests**: `backend/tests/integration/test_admin_accept_flow.py`

## API Reference

### Authentication

All endpoints use Telegram Web App `initData` for user verification. `initData` is a URL-encoded string containing:

- `user` — JSON object with user profile (id, first_name, last_name, username, etc.)
- `auth_date` — Unix timestamp
- `hash` — HMAC-SHA256 signature

**Verification**:

1. Extract `hash` from initData
2. Build check string from all other fields (sorted, newline-separated)
3. Compute `secret_key = HMAC-SHA256("WebAppData", bot_token)`
4. Compute `expected_hash = HMAC-SHA256(check_string, secret_key)`
5. Compare `hash == expected_hash`
6. Verify `time.time() - auth_date < 120` (default expiration)

### Models

### SOSenkiUser

- `id` — UUID (primary key)
- `telegram_id` — int (unique, nullable before linking)
- `email` — str (unique)
- `first_name`, `last_name` — str (optional)
- `roles` — list[str] (e.g., ["user", "administrator"])

### TelegramUserCandidate (Request)

- `id` — int (primary key)
- `telegram_id` — int (unique, not nullable)
- `username` — str (optional, from initData)
- `first_name`, `last_name` — str (optional)
- `email`, `phone` — str (optional)
- `note` — str (user's optional message, max 1024 chars)
- `status` — str ("pending", "accepted", "rejected")
- `created_at`, `updated_at` — datetime

### AdminAction (Audit)

- `id` — int (primary key)
- `admin_id` — int (SOSenkiUser.id)
- `request_id` — int (TelegramUserCandidate.id)
- `action` — str ("accept" or "reject")
- `reason` — str (optional, for reject)
- `created_at` — datetime

## Notifications

The system uses an async notification service with pluggable transports for testing and production.

### Admin Notifications

When a new request arrives, the admin group chat receives:

```text
📋 **New Access Request**
User: John Doe
Last name: Doe
Username: @john_doe
Telegram ID: `123456789`
Note: Interested in co-living spaces
```

### User Notifications

**On Accept**:

```text
✅ Your access request has been approved! You've been granted the **user** role.
```

**On Reject**:

```text
❌ Your access request has been declined. Reason: Please try again later.
```

## Testing

### Test Coverage

- **Contract Tests** (`backend/tests/contract/`): API endpoint contracts per OpenAPI spec
- **Unit Tests** (`backend/tests/unit/`): Business logic (validation, deduplication, auditing)
- **Integration Tests** (`backend/tests/integration/`): End-to-end flows with database persistence and notifications

### Running Tests

```bash
# All tests
uv run pytest backend/tests/ -v

# With coverage
uv run pytest backend/tests/ --cov=backend/app --cov-report=html

# Specific test file
uv run pytest backend/tests/integration/test_miniapp_auth.py -v

# Specific test class
uv run pytest backend/tests/integration/test_miniapp_auth.py::TestMiniAppAuthIntegration -v

# Specific test
uv run pytest backend/tests/integration/test_miniapp_auth.py::TestMiniAppAuthIntegration::test_linked_user_sees_welcome -v
```

### Mock Notifications in Tests

All tests use `MockTransport` to avoid sending real Telegram messages. To inspect notifications in a test:

```python
from backend.app.services.telegram_bot import get_telegram_bot_service

def test_something():
    # Your test code...
    bot_service = get_telegram_bot_service()
    messages = bot_service.transport.get_messages()
    # Verify notifications were sent
    assert len(messages) > 0
    assert messages[0]["chat_id"] == admin_group_id
```

## Environment Variables

See `.env.example` for required variables. Key variables for this feature:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sosenki_db

# Telegram Bot (optional for MVP)
BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=-1001234567890

# Feature flags
INITDATA_EXPIRATION_SECONDS=120
```

## File Structure

```text
backend/
├── app/
│   ├── models/
│   │   ├── user.py                 # SOSenkiUser model
│   │   ├── telegram_user_candidate.py  # Request/candidate model
│   │   └── admin_action.py         # Audit log model
│   ├── services/
│   │   ├── telegram_auth_service.py   # initData verification
│   │   ├── request_service.py         # Request creation & dedup
│   │   ├── admin_service.py           # Admin accept/reject logic
│   │   └── telegram_bot.py            # Notifications
│   ├── api/
│   │   └── routes/
│   │       ├── miniapp.py             # POST /miniapp/auth
│   │       ├── requests.py            # POST /requests
│   │       └── admin_requests.py      # Admin endpoints
│   ├── schemas/
│   │   ├── miniapp.py                 # Request/response schemas
│   │   └── requests.py                # Request schemas
│   └── main.py                        # FastAPI app initialization
├── tests/
│   ├── contract/
│   │   ├── test_miniapp_auth_contract.py
│   │   ├── test_requests_contract.py
│   │   └── test_admin_action_contract.py
│   ├── integration/
│   │   ├── test_miniapp_auth.py
│   │   ├── test_miniapp_auth_unlinked.py
│   │   ├── test_create_request_flow.py
│   │   └── test_admin_accept_flow.py
│   └── unit/
│       ├── test_initdata_validation.py
│       ├── test_request_dedup.py
│       └── test_admin_action_audit.py
└── migrations/
    └── versions/
        ├── 001_initial_schema.py
        ├── 002_add_telegram_id_to_user.py
        └── 003_create_admin_action_table.py
```

## Troubleshooting

### Tests Failing with Database Lock

SQLite (used in tests) can have concurrency issues. Solution:

```bash
# Clear pytest cache and try again
rm -rf backend/.pytest_cache backend/__pycache__
uv run pytest backend/tests/ -v
```

### Notification Service Not Initialized

If notifications fail with "No event loop", verify:

1. In production, the app calls `init_telegram_bot_service()` in `main.py`
2. In tests, MockTransport is automatically used

### initData Verification Fails

Common issues:

- Bot token mismatch between frontend and backend
- Incorrect HMAC algorithm (must be SHA256)
- `auth_date` expired (> 120 seconds old)
- User ID mismatch between request and verification

## Next Steps

- [ ] Deploy to Telegram Bot webhook (production integration)
- [ ] Add Telegram Deep Linking for invites
- [ ] Implement user role selection on accept
- [ ] Add email notifications (optional)
- [ ] Implement request search/filtering for admins
- [ ] Add rate limiting for requests
- [ ] Add request timeout/expiration logic
