# Data Model: Mini App Dashboard Redesign

**Phase**: Phase 1 - Design & Contracts  
**Date**: 2025-11-14  
**Feature**: [specs/005-mini-app-dashboard/](./spec.md)

## Overview

This document describes data entities and structures for the dashboard redesign.

**Key Principle**: No breaking database schema changes required for 005 feature. Feature uses existing User model role flags and adds one new API endpoint response schema.

**Role Clarifications**:
- **`is_owner`**: User is a property owner
- **`is_stakeholder`**: Owner's legal contract status (True = signed contract, False = not yet signed)
- **`is_tenant`**: User has rental contract with owner for specified period (NEW - for future use)

All roles displayed together on dashboard with human-readable labels.

## Existing Entities

### User Model (No Changes for 005 Feature)

Located in `src/models/user.py`. Existing table already has all required fields for this feature.

**Existing Relevant Columns**:

- `id` (Integer, Primary Key)
- `name` (String, unique)
- `telegram_id` (String, nullable)
- `is_investor` (Boolean, default=False) - Can access Invest features
- `is_administrator` (Boolean, default=False) - Can approve/reject access requests
- `is_owner` (Boolean, default=False) - Property owner (may be signed or unsigned)
- `is_staff` (Boolean, default=False) - Can view analytics/support users
- `is_stakeholder` (Boolean, default=False) - Owner's contract status (signed=True, unsigned=False)
- `is_active` (Boolean, default=True) - PRIMARY access gate for Mini App
- `created_at`, `updated_at` (DateTime with timezone)

**Role Semantics Clarification**:

- **`is_owner=True, is_stakeholder=True`**: Owner with signed legal contract
- **`is_owner=True, is_stakeholder=False`**: Owner without signed contract yet
- **`is_owner=False`**: Non-owner (can be tenant or other stakeholder role)
- **`is_tenant` (PROPOSED for future features)**: Renter/tenant with contract for specified period

**Notes for 005 Feature**:

- No schema changes needed (all fields already exist)
- Dashboard displays all active roles as read-only information
- Stakeholder status (`is_stakeholder`) shown for owners to indicate contract status
- Stakeholder shares link shown to ALL users regardless of role

## New API Response Schemas

### UserStatusResponse (New)

**Purpose**: Response from `/api/mini-app/user-status` endpoint  
**Location**: Definition in `src/api/mini_app.py` as Pydantic model

**Schema**:

```python
from pydantic import BaseModel
from typing import List, Optional

class UserStatusResponse(BaseModel):
    user_id: int
    roles: List[str]  # e.g., ["investor", "owner", "stakeholder"]
    stakeholder_url: Optional[str]  # URL from environment, may be null
    share_percentage: Optional[int]  # 1 if is_stakeholder=True (signed), 0 if is_owner=True but is_stakeholder=False (unsigned), null otherwise
```

**Field Definitions**:

- `user_id` (int): User's database ID, used for caching/validation
- `roles` (List[str]): Active roles extracted from User model boolean flags
  - Possible values: "investor", "administrator", "owner", "staff", "stakeholder", "tenant", "member"
  - "stakeholder" indicates owner with signed contract (is_owner=True AND is_stakeholder=True)
  - "tenant" indicates renter with contract (is_tenant=True)
  - Minimum: ["member"] if no roles assigned
  - Order: sorted alphabetically for consistency
- `stakeholder_url` (Optional[str]): URL to stakeholder shares document
  - Loaded from `STAKEHOLDER_SHARES_URL` environment variable
  - May be null if environment variable not set or if user is not an owner
  - Frontend does NOT render stakeholder link section if null
- `share_percentage` (Optional[int]): **CALCULATED field** (not stored in database)
  - Derived from User model flags: `is_owner` and `is_stakeholder`
  - `1` if user is owner with signed contract (is_owner=True AND is_stakeholder=True)
  - `0` if user is owner without signed contract (is_owner=True AND is_stakeholder=False)
  - `null` if user is not an owner (is_owner=False)
  - **NOTE**: This field is computed in the API response layer only; no database column required

**Example Responses**:

```json
{
  "user_id": 123,
  "roles": ["investor", "owner", "stakeholder"],
  "stakeholder_url": "https://docs.example.com/shares",
  "share_percentage": 1
}
```

```json
{
  "user_id": 456,
  "roles": ["member"],
  "stakeholder_url": null,
  "share_percentage": null
}
```

```json
{
  "user_id": 789,
  "roles": ["owner"],
  "stakeholder_url": "https://docs.example.com/shares",
  "share_percentage": 0
```
}
```

## Service Layer

### UserStatusService (New)

**Location**: `src/services/user_service.py` (add method to existing service)

**Method**: `get_active_roles(user: User) -> List[str]`

**Purpose**: Extract human-readable role labels from User model boolean flags

**Implementation Logic**:

```python
@staticmethod
def get_active_roles(user: User) -> List[str]:
    """
    Extract active roles from User model.
    Returns list of role strings or ["member"] if no roles assigned.
    
    Role semantics:
    - "owner": is_owner=True (contract status independent)
    - "stakeholder": is_owner=True AND is_stakeholder=True (owner with signed contract)
    - "tenant": is_tenant=True (renter with contract)
    - Other roles: investor, administrator, staff
    """
    roles = []
    
    # Check each role flag in order
    if user.is_investor:
        roles.append("investor")
    if user.is_administrator:
        roles.append("administrator")
    if user.is_owner:
        roles.append("owner")
    if user.is_staff:
        roles.append("staff")
    if user.is_stakeholder:
        roles.append("stakeholder")
    if hasattr(user, 'is_tenant') and user.is_tenant:  # Future: when is_tenant added
        roles.append("tenant")
    
    # Return roles or default to "member" if none assigned
    return sorted(roles) or ["member"]
```

**Return Examples**:

- Owner with signed contract: `["owner", "stakeholder"]`
- Owner without signed contract: `["owner"]`
- Renter: `["tenant"]`
- Investor with owner role: `["investor", "owner"]`
- User with no roles: `["member"]`

**DRY Principle**: Centralizes role mapping logic. Same method used by:
- Dashboard API endpoint
- Admin dashboard (future)
- Role-based access control checks
- Reporting/analytics

### Method: `get_share_percentage(user: User) -> Optional[int]`

**Purpose**: Extract stakeholder contract status indicator from User model

**Implementation Logic**:

```python
@staticmethod
def get_share_percentage(user: User) -> Optional[int]:
    """
    Return stakeholder contract status indicator for owners.
    
    Returns:
    - 1 if user is owner with signed contract (is_owner=True AND is_stakeholder=True)
    - 0 if user is owner without signed contract (is_owner=True AND is_stakeholder=False)
    - None if user is not an owner (is_owner=False)
    
    Used to display stakeholder contract status (signed=1, unsigned=0) in dashboard.
    """
    if not user.is_owner:
        return None
    return 1 if user.is_stakeholder else 0
```

**Return Examples**:

- Owner with signed contract: `1`
- Owner without signed contract: `0`
- Non-owner (tenant, investor, etc.): `None`

### Endpoint: GET /api/mini-app/user-status

**Purpose**: Provide dashboard with user roles and stakeholder information

**Request**: No body. Authenticated via existing WebApp mechanism (user_id from context).

**Response**: `UserStatusResponse` (see schema above)

**Status Codes**:
- `200 OK`: Successfully retrieved status
- `401 Unauthorized`: User not authenticated
- `404 Not Found`: User not found in database
- `500 Internal Server Error`: Backend error

**Response Headers**: `Content-Type: application/json`

**Caching**: Response may be cached client-side for 1 hour (optimization, not required for MVP)

## Frontend Data Usage

### Dashboard Initialization (JavaScript)

```javascript
// After welcome template renders
const response = await fetch('/api/mini-app/user-status');
const statusData = response.json();

// statusData.roles = ["investor", "owner"]
// statusData.stakeholder_url = "https://..."

// Create DOM elements from data
renderUserStatuses(statusData.roles);
renderStakeholderLink(statusData.stakeholder_url);
```

### Status Badges

Created from `roles` array. Each role becomes a badge element:

```html
<div class="status-badges">
  <span class="badge role-investor">Investor</span>
  <span class="badge role-owner">Owner</span>
</div>
```

### Stakeholder Link

Created from `stakeholder_url`. If URL is null or not provided:

```html
<!-- If stakeholder_url provided -->
<a href="https://docs.example.com/shares" class="stakeholder-link">
  View Stakeholder Shares
</a>

<!-- If stakeholder_url is null -->
<!-- Link not rendered, or placeholder shown -->
```

## Data Flow Diagram

1. User opens Mini App
2. GET /api/mini-app/init (existing, unchanged)
3. Render welcome template (menu items)
4. GET /api/mini-app/user-status (NEW)
5. UserStatusService.get_active_roles(user)
6. Return UserStatusResponse with roles + URL
7. Frontend renders status badges + stakeholder link
8. Dashboard ready

## Database Indexing (No Changes)

Existing indexes in User model are sufficient:

- `ix_users_is_active` - Filters active users
- `ix_users_telegram_id` - Query by telegram ID
- `ix_users_username` - Query by username
- Composite indexes on role flags already exist

**No new indexes needed** because dashboard doesn't use complex queries on role combinations.

## Migration Impact

**Migration for 005 Feature**: NONE - No database schema changes required for current feature.

**Future Migration (Tenant Support)**:
- Will add `is_tenant` (Boolean, default=False) column to User model when tenant features implemented
- No schema version conflicts: new column can be added independently
- Dashboard service already handles optional `is_tenant` flag gracefully

**Rationale**: 
- All data for 005 feature already exists in User model
- Feature only adds API layer to surface existing role data
- Tenant role prepared for future use but not required for dashboard MVP

---

**Status**: ✅ Data model complete. Ready for API contract generation.

**Next**: Phase 1 - Generate contracts and quickstart.md
