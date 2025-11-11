# Mini App API Contracts

**Feature**: 002-welcome-mini-app
**Date**: 2025-11-05
**API Version**: 1.0

## Overview

This document defines the REST API contracts for Mini App endpoints. All endpoints are served by the FastAPI backend at the root URL (e.g., `https://sosenki.host/api/mini-app/...`).

---

## Authentication

All endpoints require:
- Request origin from Telegram Mini App context
- Valid `X-Telegram-Init-Data` header containing signed user data from Telegram.WebApp.initData

**Verification**:
```python
# Backend validates signature using bot token
def verify_telegram_signature(init_data: str, bot_token: str) -> dict:
    # Parse data, validate HMAC-SHA256 signature, return user object
```

---

## Endpoint 1: Mini App Initialization

### Request

```
GET /api/mini-app/init
Headers:
  X-Telegram-Init-Data: <signed_data_from_telegram_webapp>
```

### Response (200 OK - Registered User)

```json
{
  "isRegistered": true,
  "userId": "123456789",
  "userName": "john_doe",
  "firstName": "John",
  "registeredAt": "2025-11-05T10:30:00Z",
  "menu": [
    {
      "id": "rule",
      "label": "Rule",
      "enabled": true
    },
    {
      "id": "pay",
      "label": "Pay",
      "enabled": true
    },
    {
      "id": "invest",
      "label": "Invest",
      "enabled": true
    }
  ]
}
```

### Response (200 OK - Non-Registered User)

```json
{
  "isRegistered": false,
  "message": "Access is limited",
  "instruction": "Send /request to @SG_SOSenki_Bot to request access",
  "menu": []
}
```

### Response (401 Unauthorized - Invalid Signature)

```json
{
  "error": "Invalid Telegram signature",
  "detail": "Request could not be authenticated"
}
```

### Response (500 Internal Server Error - Server Issue)

```json
{
  "error": "Server error",
  "detail": "Failed to verify registration status",
  "requestId": "uuid-here"
}
```

---

## Endpoint 2: Registration Status Check (Refresh)

### Request

```
GET /api/mini-app/verify-registration
Headers:
  X-Telegram-Init-Data: <signed_data_from_telegram_webapp>
```

**Purpose**: Explicit refresh of registration status (e.g., after cache expiration or user click "Refresh")

### Response (200 OK - Registered)

```json
{
  "isRegistered": true,
  "userId": "123456789",
  "userName": "john_doe",
  "registeredAt": "2025-11-05T10:30:00Z",
  "isActive": true,
  "lastAccessAt": "2025-11-05T14:15:00Z"
}
```

### Response (200 OK - Not Registered)

```json
{
  "isRegistered": false,
  "userId": "987654321",
  "message": "Your access request is pending or was not approved"
}
```

### Response (401 Unauthorized)

```json
{
  "error": "Invalid Telegram signature"
}
```

---

## Endpoint 3: Menu Action (Placeholder for Future)

### Request

```
POST /api/mini-app/menu-action
Headers:
  X-Telegram-Init-Data: <signed_data_from_telegram_webapp>
  Content-Type: application/json

Body:
{
  "action": "rule|pay|invest",
  "data": {}
}
```

### Response (200 OK)

```json
{
  "success": true,
  "message": "Feature coming soon!",
  "redirectUrl": null
}
```

### Response (403 Forbidden - Not Registered)

```json
{
  "error": "Access denied",
  "message": "Only registered users can access this feature"
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (regardless of registration status) |
| 401 | Invalid Telegram signature or authentication failure |
| 403 | User registered but not permitted for this action |
| 500 | Server error (database unavailable, etc.) |

---

## Rate Limiting

- `/api/mini-app/init`: 10 requests per minute per user
- `/api/mini-app/verify-registration`: 30 requests per minute per user
- Response includes `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers

---

## Error Response Format

All errors follow this standard format:

```json
{
  "error": "Error type",
  "detail": "Human-readable error message",
  "requestId": "uuid-for-tracking"
}
```

---

## Caching Strategy

- Client caches `/api/mini-app/init` result for 5 minutes in browser session storage
- Client implements manual refresh button (calls `/api/mini-app/verify-registration`)
- Server applies conditional caching (if user hasn't changed registration status, return 304 Not Modified)

---

## Telegram Signature Validation Algorithm

```
1. Extract query string from Telegram.WebApp.initData
2. Sort parameters alphabetically
3. Compute HMAC-SHA256 hash using bot token as key
4. Compare computed hash with auth_hash parameter
5. Check auth_date is within ±5 minutes of current time
6. If all checks pass, extract user object
```

---

## Future Endpoints (Out of Scope for MVP)

These are planned but NOT implemented:

- `POST /api/mini-app/settings` - User preferences (notifications, theme)
- `GET /api/mini-app/profile` - Detailed user profile
- `POST /api/mini-app/feedback` - Bug reports / feature requests
- `GET /api/mini-app/notifications` - Notification center

---

## SDK / Client Implementation

**Recommended approach** (vanilla JavaScript):

```javascript
// Load Telegram WebApp
<script src="https://telegram.org/js/telegram-web-app.js"></script>

// On app load
async function initMiniApp() {
  // WebApp.ready() is called automatically by Telegram
  const initData = window.Telegram.WebApp.initData;
  
  const response = await fetch('/api/mini-app/init', {
    method: 'GET',
    headers: {
      'X-Telegram-Init-Data': initData,
      'Content-Type': 'application/json'
    }
  });
  
  const data = await response.json();
  if (data.isRegistered) {
    displayMenu(data.menu);
  } else {
    displayAccessDenied(data.message);
  }
}

// Listen to WebApp ready event
window.Telegram.WebApp.onEvent('ready', initMiniApp);
```

---

## OpenAPI Schema (Generated)

See `mini-app-openapi.yaml` in this directory for full OpenAPI 3.0 specification.

```yaml
openapi: 3.0.0
info:
  title: SOSenki Mini App API
  version: 1.0.0
paths:
  /api/mini-app/init:
    get:
      summary: Initialize Mini App
      parameters:
        - name: X-Telegram-Init-Data
          in: header
          required: true
      responses:
        '200':
          description: Success
```
