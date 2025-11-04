# Phase 1 Data Model: Client Request Approval Workflow

**Feature**: Client Request Approval Workflow (001-request-approval)  
**Date**: 2025-11-04  
**Status**: Complete

## Entity Definitions

### ClientRequest

**Purpose**: Store and track client access requests with their approval status and timeline.

**Fields**:

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Integer (PK) | Yes | Yes | Auto-incrementing primary key |
| `client_telegram_id` | String (indexed) | Yes | No | Telegram user ID (used for lookups, pending requests) |
| `request_message` | Text | Yes | No | The message sent by the client (e.g., "Please give me access to SOSenki") |
| `status` | Enum (pending\|approved\|rejected) | Yes | No | Current state of the request (indexed for admin filtering) |
| `submitted_at` | DateTime | Yes | No | Timestamp when request was created (UTC) |
| `admin_telegram_id` | String (nullable, FK) | No | No | Administrator who responded (null if pending) |
| `admin_response` | Text (nullable) | No | No | Administrator's response message or decision note |
| `responded_at` | DateTime (nullable) | No | No | Timestamp when admin responded (UTC) |
| `created_at` | DateTime | Yes | No | Record creation timestamp (same as submitted_at for initial request) |
| `updated_at` | DateTime | Yes | No | Last modification timestamp (auto-updated on status change) |

**Constraints**:

- **Unique Constraint**: Only one PENDING request per `client_telegram_id` (prevents duplicate submissions)
- **Foreign Key**: `admin_telegram_id` references Administrator.telegram_id (soft reference via config table)
- **NOT NULL**: `client_telegram_id`, `request_message`, `status`, `submitted_at`, `created_at`, `updated_at`
- **Check Constraint**: `responded_at` must be NULL if `status = 'pending'`; must be NOT NULL if
  `status IN ('approved', 'rejected')`

**Indexes**:

- PRIMARY: `id`
- INDEX: `client_telegram_id` (for lookups, pending request validation)
- INDEX: `status` (for admin queries)
- INDEX: `submitted_at` (for timeline reports)

**State Transitions**:

```text
┌─────────────────────────────────────────┐
│ pending (initial state after /request)  │
└──────────────┬──────────────────────────┘
               │
       (admin reviews and responds)
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
  approved          rejected
  (grant access)   (deny access)
```

**Example Records**:

```json
{
  "id": 1,
  "client_telegram_id": "123456789",
  "request_message": "Please give me access to SOSenki",
  "status": "approved",
  "submitted_at": "2025-11-04T10:30:15Z",
  "admin_telegram_id": "987654321",
  "admin_response": "Welcome to SOSenki!",
  "responded_at": "2025-11-04T10:31:45Z",
  "created_at": "2025-11-04T10:30:15Z",
  "updated_at": "2025-11-04T10:31:45Z"
}
```

---

### Administrator

**Purpose**: Store configuration and metadata for administrators authorized to approve/reject requests.

**Fields**:

| Field | Type | Required | Unique | Notes |
|-------|------|----------|--------|-------|
| `telegram_id` | String (PK) | Yes | Yes | Telegram ID of the administrator (source: environment variable) |
| `name` | String | No | No | Human-readable name (e.g., "Alice") |
| `active` | Boolean | Yes | No | Whether this admin can still approve requests (default: true) |
| `created_at` | DateTime | Yes | No | When this admin was registered |
| `updated_at` | DateTime | Yes | No | Last modification timestamp |

**Constraints**:

- **Primary Key**: `telegram_id`
- **NOT NULL**: `telegram_id`, `active`, `created_at`, `updated_at`

**Notes**:

- In MVP, single administrator (loaded from environment variable `ADMIN_TELEGRAM_ID`)
- Table structure allows future multi-admin feature (YAGNI: not implemented now)
- `active` field allows soft-deactivation without deleting audit history

**Example Record**:

```json
{
  "telegram_id": "987654321",
  "name": "SOSenki Admin",
  "active": true,
  "created_at": "2025-11-04T00:00:00Z",
  "updated_at": "2025-11-04T00:00:00Z"
}
```

---

### Client (Future Expansion)

**Purpose**: Store client profiles for future feature expansion (access tracking, preferences, etc.).

**Status**: NOT IMPLEMENTED in MVP. Reserved for future use.

**Future Fields** (planning only):

| Field | Type | Notes |
|-------|------|-------|
| `telegram_id` | String (PK) | User's Telegram ID |
| `first_name` | String | User's Telegram first name |
| `username` | String (nullable) | User's Telegram username (if available) |
| `access_granted_at` | DateTime (nullable) | When access was approved (links to ClientRequest) |
| `status` | Enum (active\|inactive) | Current access status |
| `created_at` | DateTime | Record creation timestamp |

**Rationale for Deferral**: Current feature doesn't require client profiles. Telegram ID alone is
sufficient for request tracking. Adding profiles now violates YAGNI principle.

---

## Relationships

### ClientRequest → Administrator

**Type**: Many-to-One (soft foreign key)

**Direction**: ClientRequest.admin_telegram_id → Administrator.telegram_id

**Optionality**: Optional (null while pending)

**Semantics**: "An administrator responded to this request"

**Database Representation**: String foreign key (soft reference to Administrator.telegram_id)

---

## Migration Strategy (Alembic)

**Initial Migration** (`alembic/versions/001_initial_schema.py`):

1. Create `ClientRequest` table with all fields
2. Create `Administrator` table
3. Add unique constraint on `(client_telegram_id, status='pending')`
4. Create indexes on `client_telegram_id`, `status`, `submitted_at`
5. Insert initial administrator record from environment

**Future Migrations** (placeholders):

- `002_add_client_table.py` (when Client feature implemented)
- `003_add_request_audit_log.py` (if audit trail needed)

---

## Validation Rules

**ClientRequest Validation**:

- `client_telegram_id`: Non-empty string, valid Telegram ID format (9-10 digits)
- `request_message`: Non-empty string, max 4096 chars (Telegram message limit)
- `status`: One of {pending, approved, rejected}
- `submitted_at`: Valid UTC datetime, not in future
- `admin_response`: If provided, max 4096 chars
- **Check**: If `status != 'pending'`, then `responded_at` must be set and `admin_telegram_id` must be set

**Administrator Validation**:

- `telegram_id`: Non-empty string, valid Telegram ID format (9-10 digits)
- `name`: Optional, max 255 chars if provided
- `active`: Boolean (true/false)

---

## Design Decisions

**Why SQLAlchemy ORM?**

- Complies with project constitution (FastAPI + SQLAlchemy standard)
- Provides type safety and validation
- Easy to write tests with fixtures

**Why soft foreign key on admin_telegram_id?**

- Allows deletion of Administrator records without orphaning ClientRequest history
- Admin ID loaded from environment (not a full record lookup in most cases)
- Keeps schema simple (no need for Administrator.id PK)

**Why Enum for status, not separate tables?**

- Simple, readable, aligns with KISS principle
- No need for status history (current status sufficient for MVP)
- Easy to query: `db.query(ClientRequest).filter(ClientRequest.status == 'pending')`

**Why Unique Constraint on (client_telegram_id, pending)?**

- Prevents duplicate pending requests from same client
- Allows multiple historical requests (approved/rejected)
- Database-level enforcement ensures consistency

---

## Example Queries (SQLAlchemy)

```python
# Get all pending requests
pending = session.query(ClientRequest).filter(
    ClientRequest.status == 'pending'
).all()

# Get a specific client's latest request
latest = session.query(ClientRequest).filter(
    ClientRequest.client_telegram_id == '123456789'
).order_by(ClientRequest.submitted_at.desc()).first()

# Get requests approved by admin in last 24 hours
from datetime import datetime, timedelta
recent_approvals = session.query(ClientRequest).filter(
    ClientRequest.status == 'approved',
    ClientRequest.responded_at >= datetime.utcnow() - timedelta(days=1)
).all()
```

---

**Next**: API contracts in `contracts/` directory.
