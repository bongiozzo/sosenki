# API Contract: Telegram Webhook Endpoint

**Endpoint**: `POST /webhook/telegram`  
**Description**: Receives Telegram updates (messages, callbacks) and processes them through the bot handlers  
**Authentication**: None (Telegram validates via secret token in URL; see deployment docs)

## Request

### Content-Type

`application/json`

### Request Body Schema

Follows Telegram Bot API Update object (<https://core.telegram.org/bots/api#update>)

**Example - /request command from client**:

```json
{
  "update_id": 12345,
  "message": {
    "message_id": 1,
    "date": 1730702415,
    "chat": {
      "id": 123456789,
      "first_name": "John",
      "type": "private"
    },
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "John"
    },
    "text": "/request Please give me access to SOSenki"
  }
}
```

**Example - Admin approval response**:

```json
{
  "update_id": 12346,
  "message": {
    "message_id": 2,
    "date": 1730702475,
    "chat": {
      "id": 987654321,
      "first_name": "Admin",
      "type": "private"
    },
    "from": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "Admin"
    },
    "text": "Approve",
    "reply_to_message": {
      "message_id": 100,
      "text": "Client Request: John (ID: 123456789) - 'Please give me access to SOSenki'"
    }
  }
}
```

### Errors

#### HTTP 400 - Bad Request

Returned if:

- Request body is not valid JSON

- Telegram Update object is malformed

**Body**:

```json
{
  "detail": "Invalid Telegram update format"
}
```

#### HTTP 500 - Internal Server Error

Returned if:

- Database connection fails

- Bot token invalid

- Unexpected processing error

**Body**:

```json
{
  "detail": "Internal server error"
}
```

---

## Handler Contracts

### 1. /request Command Handler

**Trigger**: `message.text` starts with `/request`

**Input**: Update object with message from client

**Processing**:

1. Extract client Telegram ID from `message.from.id`
2. Extract request message from `message.text` (strip "/request" prefix)
3. Validate: client doesn't already have a PENDING request
4. Store ClientRequest record (status=pending, submitted_at=now)
5. Send confirmation message to client
6. Send notification message to admin

**Output Messages**:

**Client Confirmation**:

- To: `message.from.id` (requester)
- Text: "Your request has been received and is pending review."
- Sent within: 2 seconds

**Admin Notification**:

- To: ADMIN_TELEGRAM_ID (from config)
- Text: "Client Request: {first_name} (ID: {id}) - '{message}'"
- Includes reply keyboard with [Approve] [Reject] buttons
- Sent within: 3 seconds

**Edge Cases**:

- Client has existing PENDING request: Send error "You already have a pending request"
- Invalid admin ID in config: Log error, don't crash handler
- Database write fails: Return error to client, log server error

---

### 2. Admin Approve Handler

**Trigger**: Admin replies to request notification with text "Approve" (case-insensitive)

**Input**: Update object with message from admin (must be reply to bot's notification)

**Processing**:

1. Extract admin Telegram ID: `message.from.id`
2. Validate: `message.reply_to_message` exists (confirm admin is replying to notification)
3. Parse original request ID from reply_to_message (embedded in bot's notification)
4. Lookup ClientRequest by ID, validate status=pending
5. Update ClientRequest: status=approved, admin_telegram_id={admin}, responded_at=now, admin_response="Approved"
6. Extract client_telegram_id from ClientRequest
7. Send welcome message to client
8. Send confirmation to admin

**Output Messages**:

**Client Welcome**:

- To: ClientRequest.client_telegram_id
- Text: "Your access request has been approved! Welcome to SOSenki. [Brief next steps]"
- Sent within: 5 seconds

**Admin Confirmation**:

- To: Admin (in reply)
- Text: "Request approved and client notified."
- Sent within: 2 seconds

**Edge Cases**:

- Admin not replying to bot's notification: Send error "Please reply to a client request notification"
- Request already approved/rejected: Send error "Request already processed"
- Client Telegram ID invalid: Log error, notify admin "Failed to notify client"

---

### 3. Admin Reject Handler

**Trigger**: Admin replies to request notification with text "Reject" (case-insensitive)

**Input**: Update object with message from admin (must be reply to bot's notification)

**Processing**:

1. Extract admin Telegram ID: `message.from.id`
2. Validate: `message.reply_to_message` exists (confirm admin is replying to notification)
3. Parse original request ID from reply_to_message
4. Lookup ClientRequest by ID, validate status=pending
5. Update ClientRequest: status=rejected, admin_telegram_id={admin}, responded_at=now, admin_response="Rejected"
6. Extract client_telegram_id from ClientRequest
7. Send rejection message to client
8. Send confirmation to admin

**Output Messages**:

**Client Rejection**:

- To: ClientRequest.client_telegram_id
- Text: "Your access request has been reviewed and was not approved at this time."
- Sent within: 5 seconds

**Admin Confirmation**:

- To: Admin (in reply)
- Text: "Request rejected and client notified."
- Sent within: 2 seconds

**Edge Cases**:

- Admin not replying to bot's notification: Send error "Please reply to a client request notification"
- Request already approved/rejected: Send error "Request already processed"
- Client Telegram ID invalid: Log error, notify admin "Failed to notify client"

---

## Contract Testing

**Test File**: `tests/contract/test_request_endpoint.py`

**Test Cases**:

1. POST /webhook/telegram with valid /request update → HTTP 200 + client receives confirmation
2. POST /webhook/telegram with valid Approve response → HTTP 200 + client receives welcome
3. POST /webhook/telegram with valid Reject response → HTTP 200 + client receives rejection
4. POST /webhook/telegram with malformed JSON → HTTP 400
5. POST /webhook/telegram with missing required fields → HTTP 400
6. POST /webhook/telegram when database unavailable → HTTP 500 (error message in logs, HTTP response sent)

---

**Next**: Create `quickstart.md` for local development setup.
