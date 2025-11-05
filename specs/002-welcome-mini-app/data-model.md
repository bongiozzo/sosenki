# Data Model: Welcome Mini App for Approved Users

**Feature**: 002-welcome-mini-app
**Date**: 2025-11-05
**Phase**: 1 (Design & Contracts)

## Overview

This document defines the data entities, schema, and relationships required for the Welcome Mini App feature. The design follows a unified user model architecture where:

- **User**: Core user entity representing any person in the system (can hold multiple roles simultaneously)
- **AccessRequest**: Request from a client seeking access to SOSenki (replaces ClientRequest; serves as audit log)
- **Approval Workflow**: Connects AccessRequest to User registration when approved

This refactoring replaces the separate `ClientRequest` and `Administrator` models with a unified `User` model. Users can hold multiple roles (e.g., can be both Administrator and Owner), improving consistency and maintainability across all features. **Principle**: YAGNI - only tables needed for the feature are created. ApprovalNotification is not required (welcome message already sent via 001-request-approval webhook; audit trail exists in AccessRequest records).

---

## Entities & Schema

### 0. User (Core - Unified Model, Multiple Roles)

**Purpose**: Central user entity representing any person in the system. Users can hold multiple roles simultaneously (e.g., Administrator AND Owner AND Staff).

**Fields**:

- `id` (Integer, Primary Key)
- `telegram_id` (String, Not Null, Unique, Indexed) - Primary identifier
- `username` (String, Nullable, Indexed) - Telegram username
- `first_name` (String, Nullable) - User's first name
- `last_name` (String, Nullable) - User's last name
- `is_investor` (Boolean, Default: False) - Can access Invest features in Mini App (requires is_active=True)
- `is_administrator` (Boolean, Default: False) - Can approve/reject access requests
- `is_owner` (Boolean, Default: False) - Can manage system configuration (future)
- `is_staff` (Boolean, Default: False) - Can view analytics and support users (future)
- `is_active` (Boolean, Default: True) - Can access Mini App (primary access gate)
- `created_at` (DateTime, Not Null) - Account creation timestamp
- `updated_at` (DateTime, Not Null) - Last update timestamp

**Indexes**:

- `telegram_id` (Unique lookup)
- `is_active` (Filter active users - primary access gate)
- `(is_investor, is_active)` (Fast lookup for approved investors)

**State Examples**:

- New user (not yet approved): `is_active=False` (cannot access Mini App)
- Active user (can access Mini App): `is_active=True`
- Investor (can access Invest features): `is_investor=True, is_active=True`
- Administrator: `is_administrator=True, is_active=True` (configured externally)
- Admin + Owner: `is_administrator=True, is_owner=True, is_active=True` (multiple roles)
- Deactivated user: `is_active=False` (preserves all role flags; can be reactivated)

**Purpose of unified User model with multiple roles**:
- Mini App access controlled by `is_active` (single gate for all users)
- Feature-level access via role flags: `is_investor` for Invest features, etc.
- Supports users with multiple roles simultaneously
- Single source of truth eliminates duplication
- Flexible role assignments without schema changes
- Audit trail preserved via is_active flag (never delete)
- Scales to future features without schema redesign

---

### 1. AccessRequest (Renamed from ClientRequest - Audit Log)

**Purpose**: Tracks all access requests from users seeking approval to use SOSenki. **This table serves as the immutable audit log** for approval workflows. **No separate ApprovalNotification table needed** - welcome message already sent via 001-request-approval webhook; full history is maintained here. Redundant timestamp fields removed per YAGNI.

**Existing fields** (from 001-request-approval, renamed/refactored):

- `id` (Integer, Primary Key)
- `user_telegram_id` (String, Not Null, Foreign Key → User.telegram_id, Indexed)
- `request_message` (String, Not Null)
- `status` (Enum: pending/approved/rejected, Not Null)
- `submitted_at` (DateTime, Not Null, Indexed)
- `responded_by_admin_id` (String, Nullable, Foreign Key → User.telegram_id) - Admin who responded
- `response_message` (String, Nullable)
- `responded_at` (DateTime, Nullable) - When admin approved/rejected

**Indexes**:

- `(user_telegram_id, status)` - Fast lookup for user's request status
- `status` - Filter pending/approved/rejected
- `submitted_at` - Timeline queries
- `responded_by_admin_id` - Audit: who approved/rejected

**State Transitions**:

```
pending → approved (set responded_at=now(), User.is_active=True)
pending → rejected (User.is_active remains False)
```

**Relationship**:
- AccessRequest.user_telegram_id → User (client making request)
- AccessRequest.responded_by_admin_id → User (admin reviewing request)

---

### 2. MiniAppSession (New - Optional Analytics)

**Purpose**: Track Mini App user sessions for analytics and debugging. **Optional** - can be deferred if analytics not needed (YAGNI). Useful for understanding Mini App usage patterns but not required for core functionality.

**Purpose**: Track Mini App user sessions (optional, for analytics and debugging)

**Fields**:

- `id` (Integer, Primary Key)
- `user_telegram_id` (String, Not Null, Foreign Key → User.telegram_id, Indexed)
- `session_start_at` (DateTime, Not Null)
- `session_end_at` (DateTime, Nullable)
- `user_is_active_at_load` (Boolean) - Was user.is_active=True when Mini App loaded
- `menu_items_viewed` (JSON Array, Nullable) - e.g., ["Rule", "Pay"]
- `error_messages` (JSON Array, Nullable) - e.g., ["Network timeout"]
- `access_request_id` (Integer, Foreign Key → AccessRequest.id, Nullable)

**Indexes**:

- `user_telegram_id` + `session_start_at` - Lookup sessions for a user
- `session_start_at` - Timeline reporting

**Purpose**: Optional but useful for:
- Debugging ("did user's Mini App load successfully?")
- Analytics ("which menu items are users viewing?")
- Error tracking ("what errors occurred in Mini App?")

**Relationship**:
- MiniAppSession.user_telegram_id → User
- MiniAppSession.access_request_id → AccessRequest (optional, for correlation)

---

## Data Flow & State Transitions

### Approval Workflow (extends 001-request-approval):

```
1. User sends /request (User created with is_active=False)
   → AccessRequest created with status=pending
2. Admin approves (via Telegram bot, 001-request-approval webhook)
3. AccessRequest.status → approved, responded_at = now()
   → Webhook sends Welcome message with Mini App link (from 001 feature)
4. User.is_active → True (account activated; can access Mini App)
5. User opens Mini App link
6. Mini App queries User (telegram_id lookup with is_active=True)
7. User sees welcome message + menu (or "Access limited" if is_active=False)
8. MiniAppSession created (optional, for analytics)
```

### Access Verification:

```
GET /api/mini-app/init
  1. Extract user from Telegram.WebApp.initData
  2. Verify Telegram signature (HMAC-SHA256)
  3. Query: SELECT * FROM user WHERE telegram_id=? AND is_active=True
  4. If found: Return { hasAccess: true, userName, isInvestor, ... }
  5. If not found: Return { hasAccess: false, message: "Access is limited" }
  6. Create MiniAppSession record (optional)
```

### Feature-Level Access Example (Future):

```
User opens Invest feature:
  → Check User.is_investor=True
  → If True: Display Invest features
  → If False: Display "Coming soon" or "Not available"

User can be active (Mini App access) but not investor (no Invest features):
  → User.is_active=True, User.is_investor=False
  → Sees menu but Invest option is disabled/locked
```

### Multiple Roles Example:

```
Administrator user:
  → User.is_administrator=True, User.is_active=True
  → Can approve requests, manage users

User can be both Administrator AND Investor:
  → User.is_administrator=True AND User.is_investor=True
  → Can do both: approve requests AND access Invest features
```

### Revocation (Soft Delete):

```
UPDATE user SET is_active=False WHERE telegram_id=?
(No deletion—audit trail preserved via AccessRequest records)

SELECT * FROM access_request WHERE user_telegram_id=? ORDER BY submitted_at DESC
→ Full approval history retained, even if user is deactivated
```

---

## Database Migration Path

### Alembic Migration File: `[timestamp]_add_welcome_mini_app_schema.py`

**Operations**:

1. Create `user` table (if not exists from 001-request-approval):
   - telegram_id (String, Primary Key + Unique Index)
   - username (String, nullable, indexed)
   - first_name, last_name (String, nullable)
   - is_investor (Boolean, default=False)
   - is_administrator (Boolean, default=False)
   - is_owner (Boolean, default=False)
   - is_staff (Boolean, default=False)
   - is_active (Boolean, default=True, indexed) - PRIMARY ACCESS GATE
   - created_at, updated_at (DateTime)

2. Refactor `client_requests` table (rename to `access_requests`):
   - Rename table: client_requests → access_requests
   - Rename client_telegram_id → user_telegram_id
   - Rename admin_telegram_id → responded_by_admin_id
   - Rename submitted_timestamp → submitted_at
   - Keep response_message, responded_at fields (no new timestamp fields needed)
   - Add foreign key: user_telegram_id → user.telegram_id
   - Add foreign key: responded_by_admin_id → user.telegram_id (nullable)
   - Update indexes: (user_telegram_id, status), status, submitted_at, responded_by_admin_id

3. Data migration:
   - No historical data migration needed for MVP (fresh feature branch)
   - AccessRequest table will be populated as new requests come in

4. Optional: Create `mini_app_session` table (skip if deferring analytics per YAGNI):
   - id, user_telegram_id (FK), session_start_at, session_end_at
   - user_is_active_at_load (Boolean), menu_items_viewed (JSON), error_messages (JSON)
   - access_request_id (FK, optional)

---

## Validation Rules

### User:

- `telegram_id` must be non-empty, unique string (valid Telegram user ID format)
- `is_investor`, `is_administrator`, `is_owner`, `is_staff` are independent booleans (can be true simultaneously)
- `is_active` controls primary Mini App access (default True on creation; set False for soft-delete)
- `created_at` and `updated_at` auto-set on creation/modification
- Administrators can only be created/managed via configuration (not self-registration)

### AccessRequest:

- `user_telegram_id` must reference existing User record
- `responded_by_admin_id` must reference User with is_administrator=True (if set)
- `status` valid values: pending, approved, rejected
- `submitted_at` immutable after creation
- When status transitions to 'approved': automatically set User.is_active=True
- Response fields (response_message, responded_at) updated only when admin responds

### MiniAppSession (Optional):

- `user_telegram_id` must reference existing User
- `session_end_at` must be >= `session_start_at` (if set)
- `user_is_active_at_load` immutable after creation (snapshot of User.is_active at load time)
- `access_request_id` optional, may be null (for non-approved user sessions)

---

## Performance Considerations

### Query Patterns:

1. **Most frequent**: `SELECT * FROM user WHERE telegram_id=?`
   - Index: `(telegram_id)`
   - Expected: <1ms (indexed lookup)

2. **On approval**: `INSERT INTO access_request...`
   - No complex joins
   - Expected: <10ms

3. **Audit**: `SELECT * FROM access_request WHERE status='approved' ORDER BY responded_at DESC`
   - Index: `status`, `responded_at`
   - Expected: <50ms for 10k records

4. **Analytics**: `SELECT COUNT(*) FROM user WHERE is_active=True`
   - Index: `is_active`
   - Expected: <100ms

### Storage Estimates (MVP scale):

- `User`: ~100-1000 records → ~50KB
- `AccessRequest`: ~100-1000 records → ~100KB
- `MiniAppSession` (optional): ~1000-10k records (sessions) → ~5MB

**Total**: <10MB for first year of MVP usage (minimal storage footprint per YAGNI)

---

## Relationships Diagram

```
User (unified model - multiple independent roles)
  ├── is_active=False              → Cannot access Mini App
  ├── is_active=True               → Can access Mini App (primary gate)
  ├── is_investor=True             → Can access Invest features (requires is_active=True)
  ├── is_administrator=True        → Can approve access requests
  ├── is_owner=True                → Can manage configuration (future)
  ├── is_staff=True                → Can view analytics (future)
  └── Multiple roles simultaneously → e.g., is_admin=True AND is_owner=True
         ↑
         │ (user_telegram_id)
         │
    AccessRequest ←─── AUDIT TRAIL (full history preserved)
         │              (no deletion; soft-delete via User.is_active)
         │ (responded_by_admin_id)
         ↓
    (admin User with is_administrator=True)

    MiniAppSession (OPTIONAL, for analytics)
         │ (user_telegram_id)
         ↓
    User (captures session stats)
```

**Key**: 
- `is_active` is the PRIMARY access gate to Mini App
- Feature-level access via role flags: `is_investor` for Invest features, etc.
- AccessRequest serves as immutable audit log
- Welcome notification sent via 001-request-approval webhook

---

## Future Extensibility (Out of Scope - Not Implemented in MVP per YAGNI)

These are mentioned for documentation but NOT created in initial schema:

- User preferences table (theme, notifications, language)
- Permission matrix (detailed per-role permissions)
- Audit log table (comprehensive change tracking)
- User groups/organizations (team management)
- Device tracking (device_id, OS, client version)

**These can be added later without breaking existing schema** (new tables, no modifications to existing User/AccessRequest).

---

## Next Steps

- SQL migration file will be generated by Alembic
- API contracts will define serialization format for JSON responses
- Quickstart will include schema diagrams and connection string examples
