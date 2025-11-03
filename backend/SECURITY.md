# Security Documentation: 001-seamless-telegram-auth

## Overview

The "Seamless Telegram Auth" feature implements Telegram Web App initData verification for user authentication and identity validation. This document outlines security considerations, threat mitigation, and best practices.

---

## 1. Telegram initData Verification

### Security Model

Telegram Web App initData is cryptographically signed by Telegram's servers. SOSenki verifies this signature to ensure:

- The user information (telegram_id, first_name, username) originates from Telegram
- The data has not been tampered with
- The request is recent (within 120 seconds)

### Verification Algorithm

**Implementation**: `backend/app/services/telegram_auth_service.py`

```plaintext
1. Parse initData (URL-encoded parameters):
   - user: JSON object with user profile
   - auth_date: Unix timestamp
   - hash: HMAC-SHA256 signature

2. Build check string:
   - Extract all fields except "hash"
   - Sort alphabetically
   - Join with newline separator
   Example: "auth_date=1699000000\nuser=%7B...%7D"

3. Compute secret key:
   - HMAC-SHA256("WebAppData", bot_token) -> 32-byte key

4. Verify hash:
   - expected_hash = HMAC-SHA256(check_string, secret_key).hex()
   - Compare with provided hash (constant-time comparison)

5. Verify timestamp:
   - Ensure auth_date is within INITDATA_EXPIRATION_SECONDS (default 120s)
   - Protects against replay attacks
```

### Threat Mitigation

| Threat | Mitigation |
|--------|-----------|
| **Signature Forgery** | HMAC-SHA256 requires secret bot_token; attacker cannot forge valid hash |
| **Tampering** | Hash mismatch detected; request rejected with 401 |
| **Replay Attack** | auth_date timestamp verification; stale requests rejected |
| **User Impersonation** | Hash covers user object; attacker cannot swap telegram_id |
| **Cloning/Forking App** | Different bot_token per instance; clone gets different hash |

### Key Management

**Bot Token Storage**:

- ✅ **CORRECT**: Stored in environment variable `BOT_TOKEN`
- ❌ **INCORRECT**: Hardcoded in source, committed to git, logged
- ⚠️ **WARNING**: Single bot token compromised = all sessions compromised

**Recommendations**:

- Rotate bot token periodically via Telegram BotFather
- Store in secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)
- Enable audit logging for token access
- Restrict environment variable access to deployment service

---

## 2. Request Submission & Deduplication

### Security Considerations

**TelegramUserCandidate** (pending requests) contains sensitive user data:

- telegram_id, username, email, phone, name
- Should be treated as PII

### Deduplication Strategy

**Purpose**: Prevent spam, brute-force requests

**Implementation**: `backend/app/services/request_service.py`

- Unique constraint on `telegram_id` in TelegramUserCandidate table
- Database-level enforcement (integrity constraint)
- Duplicate attempt returns 400 Bad Request

**Database Schema**:

```sql
CREATE TABLE telegram_user_candidate (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,  -- Prevents duplicates
    username VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    note TEXT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Risk**: Without deduplication, attacker could submit many requests to:

- Spam admin notifications
- Enumerate valid telegram_ids
- DDoS the system

---

## 3. Admin Authorization

### Role-Based Access Control (RBAC)

**Admin Endpoints** (`POST /admin/requests/{id}/action`):

- Requires `admin_id` in request body
- Verifies admin_id corresponds to SOSenkiUser with "Administrator" role
- Audit trail: AdminAction record logs who did what

**Threat**: Unauthorized admin action

**Mitigation**:

- Validate admin_id existence and role (TODO: implement role check in admin_requests.py)
- Log all admin actions for audit
- Consider JWT/session-based auth for production

**TODO - Production Hardening**:

```python
# Current: Trusts admin_id from request body
# Required: Verify role before action

def verify_admin_authorization(db: Session, admin_id: int) -> bool:
    admin = db.query(SOSenkiUser).filter_by(id=admin_id).first()
    return admin and "Administrator" in admin.roles
```

---

## 4. User Notifications

### Telegram Bot Security

**Notification Transport** (`backend/app/services/telegram_bot.py`):

- Abstract transport for pluggable implementations
- MockTransport (testing) vs. RealTransport (production)
- Async fire-and-forget pattern (non-blocking)

**Threats**:

- Notifying wrong user (telegram_id mismatch)
- Sending sensitive data unencrypted

**Mitigations**:

- Verify telegram_id matches request before sending
- Telegram API connection is HTTPS-encrypted
- Bot token required for sending (only backend has it)
- Rate limiting on Telegram Bot API (prevents abuse)

**Production Implementation** (not in MVP):

```python
class TelegramBotTransport(NotificationTransport):
    def __init__(self, bot_token: str):
        self.bot_token = bot_token  # From secure env var
        self.api_url = "https://api.telegram.org"
    
    async def send_message(self, chat_id: int, message: str) -> bool:
        # Validates chat_id and sends via HTTPS
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/bot{self.bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message}
            )
            return response.status_code == 200
```

---

## 5. Data Privacy & PII Handling

### Personal Information in Scope

- **telegram_id**: Telegram's public user identifier
- **username**: Publicly visible @username
- **first_name, last_name**: User profile data
- **email, phone**: User-provided contact info
- **note**: User's optional message

### Storage & Access

**TelegramUserCandidate** (request):

- Stored in PostgreSQL with standard encryption at rest
- Accessible by: admins (via dashboard), backend (for verification)
- Retention: Indefinite (consider archival policy)

**SOSenkiUser** (linked user):

- Created after admin approval
- Contains same PII (copied from request)
- User has data access rights (future: implement /user/profile endpoint)

### Data Minimization

**Current**:

- Collect minimal fields: telegram_id, first_name, username, email (optional), phone (optional)
- Request form limits note to 1024 chars

**Consider**:

- Delete rejected requests after 30 days
- Anonymize old data (>1 year)
- Implement GDPR right-to-be-forgotten

---

## 6. Injection & Injection Attacks

### SQL Injection

**Status**: ✅ **PROTECTED**

**Mechanism**: SQLAlchemy ORM (parameterized queries)

- All queries use bound parameters
- User input never interpolated into SQL strings

**Example (Safe)**:

```python
candidate = db.query(TelegramUserCandidate).filter_by(telegram_id=telegram_id).first()
# telegram_id is bound parameter, not string interpolation
```

### XSS (Cross-Site Scripting)

**Status**: ✅ **PROTECTED** (Backend API)

**Mechanism**: This is a REST API, not HTML rendering

- No direct HTML output
- JSON responses are data, not executable
- Frontend is responsible for XSS prevention

### Command Injection

**Status**: ✅ **PROTECTED**

**Mechanism**: No shell commands executed

- No `subprocess`, `shell=True`, or `os.system` calls
- All external services use libraries (httpx for HTTP)

---

## 7. Rate Limiting & DoS Prevention

### Current

**Request Submission**:

- Deduplication per telegram_id (max 1 request per user)
- Database constraint prevents duplicates

**Admin Actions**:

- No rate limit (assumes internal use)
- Audit trail for accountability

### Recommended (Production)

```python
# Per-user request rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/requests")
@limiter.limit("5/hour")  # Max 5 requests per IP per hour
async def submit_request(payload: CreateRequestPayload):
    ...
```

### Telegram Bot API Rate Limiting

- Built into Telegram API (rate limits to prevent abuse)
- If exceeded: HTTP 429 (Too Many Requests)
- Current implementation gracefully handles (logs error, continues)

---

## 8. Secrets & Environment Variables

### Required Secrets

| Variable | Purpose | Risk if Leaked |
|----------|---------|--------------|
| `BOT_TOKEN` | Telegram Bot authentication | Attacker can send messages, control bot |
| `DATABASE_URL` | PostgreSQL connection | Attacker has DB access |
| `SECRET_KEY` (future) | JWT signing | Session hijacking |

### Storage

**.env.example** (committed, no secrets):

```bash
BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@localhost:5432/sosenki_db
```

**.env** (NOT committed, contains real secrets):

```bash
BOT_TOKEN=123456:ABCDEfghijklmnop
DATABASE_URL=postgresql://produser:SecurePassword@prod.db:5432/sosenki
```

### Best Practices

- ✅ Use secure secret management (AWS Secrets Manager, Vault)
- ✅ Rotate secrets periodically
- ✅ Restrict environment variable access
- ✅ Enable audit logging on secret access
- ✅ Never log secrets (Python logging module masks them)
- ❌ Never commit `.env` or secrets to git
- ❌ Never print secrets in logs or responses

---

## 9. Testing Security

### Test Isolation (MockTransport)

**Purpose**: Tests don't send real Telegram messages

**Implementation**:

```python
# Test setup uses MockTransport
def test_something(test_db_session):
    # MockTransport stores messages in memory
    bot_service = get_telegram_bot_service()
    assert isinstance(bot_service.transport, MockTransport)
    
    # Verify notifications without hitting real API
    messages = bot_service.transport.get_messages()
    assert len(messages) == 1
```

### Contract Tests

**File**: `backend/tests/contract/`

- Verify API responses match OpenAPI schema
- Test invalid initData rejection (401)
- Test expired auth_date rejection
- Test missing/tampered hash rejection

### Unit Tests

**File**: `backend/tests/unit/`

- `test_initdata_validation.py`: Hash verification logic
- `test_request_dedup.py`: Deduplication enforcement
- `test_admin_action_audit.py`: Audit trail creation

---

## 10. Known Limitations & Future Work

### MVP Limitations

- [ ] Admin role verification not enforced (assumes internal endpoints)
- [ ] No rate limiting on request submission
- [ ] No data retention/archival policy
- [ ] No end-to-end encryption for sensitive fields
- [ ] No OTP/2FA for admin actions
- [ ] No IP whitelisting for admin endpoints

### Production Hardening

- [ ] Implement RBAC enforcement: verify admin_id has "Administrator" role
- [ ] Add rate limiting: slowapi or similar
- [ ] Implement audit logging: log all data access
- [ ] Add request signing: digitally sign requests between backend and frontend
- [ ] Implement CAPTCHA: prevent bot submissions
- [ ] Add IP whitelisting: restrict admin endpoints to known IPs
- [ ] Database encryption: enable PostgreSQL encryption at rest
- [ ] TLS/SSL: enforce HTTPS everywhere

---

## 11. Security Checklist

Before deploying to production:

- [ ] Bot token stored in secure vault (not .env file)
- [ ] Database password strong (>20 chars, random)
- [ ] HTTPS enabled (TLS 1.3+)
- [ ] CORS configured correctly (restrict origins)
- [ ] Admin endpoints behind authentication
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Secrets never logged or printed
- [ ] Database backups encrypted
- [ ] Secrets rotation policy defined
- [ ] Incident response plan created
- [ ] Security testing completed (OWASP Top 10)
- [ ] Penetration testing completed (3rd party)
- [ ] Security review approved (CISO or equiv.)

---

## 12. Incident Response

### If Bot Token Compromised

1. Immediately revoke token in BotFather
2. Generate new token
3. Update environment variables
4. Redeploy application
5. Audit logs for unauthorized activity
6. Notify users if applicable

### If Database Compromised

1. Shut down application
2. Backup database (for forensics)
3. Restore from clean backup
4. Audit logs for unauthorized access
5. Force password reset for all users
6. Notify security team

---

## References

- [Telegram Bot API Security](https://core.telegram.org/bots/api-security)
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
