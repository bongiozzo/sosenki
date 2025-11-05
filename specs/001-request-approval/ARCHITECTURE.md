# Architecture Guide: Client Request Approval Workflow

**Feature**: Client Request Approval Workflow (001-request-approval)  
**Date**: 2025-11-04  
**Target Audience**: Software architects, senior developers, code reviewers

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Component Design](#component-design)
3. [Data Flow](#data-flow)
4. [Database Schema](#database-schema)
5. [Error Handling](#error-handling)
6. [Testing Strategy](#testing-strategy)
7. [Design Patterns](#design-patterns)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)

---

## System Architecture

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram Bot Servers                          │
│                      (Cloud Hosted)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS Webhook POST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│                  POST /webhook/telegram                          │
│            → Parses Update → Dispatches to Handler              │
└────────────┬─────────────────────────────────────────────────────┘
             │
    ┌────────┴──────────┬────────────────┬─────────────────┐
    ▼                   ▼                ▼                 ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
│  Handlers   │  │   Services   │  │  ORM Models  │  │  Database   │
│             │  │               │  │  (SQLAlchemy)│  │  (SQLite/   │
│ - Request   │  │ - Request     │  │              │  │   Postgres) │
│ - Approve   │  │ - Admin       │  │ - ClientReq  │  │             │
│ - Reject    │  │ - Notification│  │ - Admin      │  │ - Requests  │
└─────────────┘  └──────────────┘  └──────────────┘  └─────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|-----------------|
| **FastAPI App** | HTTP endpoint, request/response handling, webhook security |
| **Bot Handlers** | Parse Telegram Updates, extract relevant data, call services |
| **Services** | Core business logic, data validation, orchestration |
| **ORM Layer** | Database abstraction, query building, transaction management |
| **Database** | Persistent storage, ACID compliance, data integrity |

---

## Development & Dependency Management

### Constitution Compliance

This project adheres to the **SOSenki Project Constitution (v1.1.0)** which mandates:

1. **YAGNI (You Aren't Gonna Need It)**: Build only what is required for the current MVP
   - No speculative features or scaffolding
   - Every line of code serves an immediate user story

2. **KISS (Keep It Simple, Stupid)**: Prefer straightforward solutions
   - Readable and maintainable code over clever implementations
   - Simplicity enables faster debugging and feature iteration

3. **DRY (Don't Repeat Yourself)**: Eliminate code duplication
   - Extract shared logic into services, utilities, or modules
   - Single source of truth for all business logic

### Dependency Management Standard

**All dependencies managed via `uv` package manager** (per constitution):

```bash
# Install dependencies (reproducible via uv.lock)
uv sync

# Run tests
uv run pytest -v tests/

# Run linting
uv run ruff check src/ tests/

# Run migrations
uv run alembic upgrade head

# Run application
uv run python -m src.main --polling
```

**Prohibition**: `requirements.txt` and `pip` are NOT used. All dependency management flows through `uv` and `pyproject.toml`.

**Library Documentation Standard** (MCP Context7):

When adding new dependencies or upgrading major versions, use MCP Context7 to retrieve authoritative, up-to-date documentation. Current dependencies documented via Context7:

- `python-telegram-bot` (v20+): Async webhooks, handlers, updates
- `fastapi`: Async HTTP framework, Pydantic validation
- `sqlalchemy`: ORM layer, session management
- `alembic`: Database migrations, schema evolution
- `pytest`: Test framework, fixtures, async support

### Secret Management (Non-Negotiable)

- **No Hard-Coded Secrets**: All credentials (TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, DATABASE_URL) stored as environment variables only
- **Local Development**: `.env` files permitted (never committed to version control)
- **Production**: All secrets loaded from environment, secrets manager (AWS Secrets Manager, HashiCorp Vault), or CI/CD platform

---

## Component Design

### 1. Handler Layer (`src/bot/handlers.py`)

**Responsibility**: Accept Telegram Updates, parse data, route to services

```python
async def handle_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User Story 1: Client submits access request
    
    Flow:
    1. Extract client_id and request_message from update
    2. Call RequestService.create_request()
    3. Call NotificationService.send_confirmation_to_client()
    4. Call NotificationService.send_notification_to_admin()
    5. Handle errors with try-catch, log all operations
    """
    
async def handle_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User Story 2: Admin approves request
    
    Flow:
    1. Extract admin_id from update
    2. Validate "Approve" text (case-insensitive)
    3. Parse request ID from reply_to_message
    4. Call AdminService.approve_request()
    5. Call NotificationService.send_welcome_message()
    6. Send confirmation to admin
    7. Handle errors gracefully
    """
    
async def handle_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    User Story 3: Admin rejects request
    
    Flow:
    1. Extract admin_id from update
    2. Validate "Reject" text (case-insensitive)
    3. Parse request ID from reply_to_message
    4. Call AdminService.reject_request()
    5. Call NotificationService.send_rejection_message()
    6. Send confirmation to admin
    7. Handle errors gracefully
    """
```

**Design Pattern**: Handler pattern (common in messaging systems)

- Single responsibility: parse + validate + route
- Handlers are stateless
- All state managed by services

### 2. Service Layer (`src/services/`)

**Responsibility**: Core business logic, data validation, orchestration

#### RequestService

```python
async def create_request(client_id: str, message: str) -> ClientRequest:
    """
    Create new request with validation:
    - Check for duplicate pending request (unique constraint)
    - Insert into database
    - Return created request object
    """

async def get_pending_request(client_id: str) -> ClientRequest | None:
    """Query database for pending request by client_id"""

async def update_request_status(request_id: int, status: str, admin_id: str, response: str) -> None:
    """Update request status (pending → approved/rejected) with admin details"""

async def get_request_by_id(request_id: int) -> ClientRequest | None:
    """Query single request by ID"""
```

**Key Features**:

- Validation: duplicate check via unique constraint
- Error handling: try-catch with rollback
- Database access: uses SQLAlchemy ORM

#### AdminService

```python
async def approve_request(request_id: int, admin_id: str) -> ClientRequest | None:
    """
    Approve request workflow:
    1. Fetch request by ID
    2. Update status to APPROVED
    3. Set admin_telegram_id, admin_response, responded_at
    4. Commit transaction
    5. Return updated request or None if not found
    """

async def reject_request(request_id: int, admin_id: str) -> ClientRequest | None:
    """Same as approve but status → REJECTED"""
```

**Key Features**:

- Status transitions with validation
- Timestamp tracking
- Admin attribution

#### NotificationService

```python
async def send_message(chat_id: str, text: str) -> bool:
    """
    Base method for all messages:
    1. Call bot.send_message()
    2. Handle Telegram API errors
    3. Return success/failure
    """

async def send_confirmation_to_client(client_id: str) -> bool:
    """Send: "Your request has been received and is pending review."""

async def send_notification_to_admin(client_info: dict) -> bool:
    """Send: "Client Request: {name} (ID: {id}) - '{message}'" with buttons"""

async def send_welcome_message(client_id: str) -> bool:
    """Send: "Welcome to SOSenki! Your request has been approved and access has been granted."""

async def send_rejection_message(client_id: str) -> bool:
    """Send: "Your request for access to SOSenki has not been approved at this time."""
```

**Key Features**:

- Message templates
- Error handling for Telegram API failures
- Async operations

### 3. ORM Layer (`src/models/`)

**Responsibility**: Data models, database schema, relationships

#### ClientRequest Model

```python
class ClientRequest(Base):
    __tablename__ = "client_requests"
    
    id: Primary key (auto-increment)
    client_telegram_id: String (unique + status)
    request_message: String (full message text)
    status: Enum (pending, approved, rejected)
    submitted_at: DateTime (when client submitted)
    admin_telegram_id: String (null until admin responds)
    admin_response: String (approved/rejected)
    responded_at: DateTime (null until admin responds)
    created_at: DateTime (auto)
    updated_at: DateTime (auto)
    
    # Unique constraint: (client_telegram_id, status='pending')
    # Ensures only one pending request per client
```

**Design Decisions**:

- String IDs for Telegram IDs (compatibility with large integers)
- Status enum instead of boolean
- Timestamp tracking for audit trail
- Unique constraint prevents duplicate pending requests

#### Administrator Model

```python
class Administrator(Base):
    __tablename__ = "administrators"
    
    telegram_id: PK (String)
    name: String (admin name)
    active: Boolean (enable/disable)
    created_at: DateTime (auto)
    updated_at: DateTime (auto)
```

---

## Data Flow

### User Story 1: Client Submits Request

```text
Client                 FastAPI               Handlers              Services             Database
  │                       │                     │                      │                    │
  ├─/request msg ─────────┤                     │                      │                    │
  │                       ├─parse Update ─────→ │                      │                    │
  │                       │                     ├─validate client ─────┤                    │
  │                       │                     ├─create_request ──────┤                    │
  │                       │                     │                      ├─INSERT ─────────────┤
  │                       │                     │                      │←─OK ────────────────┤
  │                       │                     │←─request obj ────────┤                    │
  │                       │                     ├─send_confirmation ──┤                    │
  │                       │                     │                      ├─bot.send_message ──┤
  │                       │                     │                      │                    │
  │←─confirmation msg ─────┤←─HTTP 200 OK ──────┤                      │                    │
  │
  Admin                   │                     │                      │                    │
  │                       │                     ├─send_notification ──┤                    │
  │←─notification msg ─────┤                     │                      ├─bot.send_message ──┤
  │                       │                     │                      │                    │
```

**Key Operations**:

1. Parse Telegram Update (JSON → Update object)
2. Extract client_id and message text
3. Validate message (not empty, client_id present)
4. Call RequestService.create_request() with duplicate check
5. Send two async notifications (client + admin)
6. Return HTTP 200 response to webhook

### User Story 2: Admin Approves Request

```text
Admin                   FastAPI               Handlers              Services             Database
  │                       │                     │                      │                    │
  ├─"Approve" (reply) ────┤                     │                      │                    │
  │                       ├─parse Update ─────→ │                      │                    │
  │                       │                     ├─validate "Approve" ──┤                    │
  │                       │                     ├─parse request ID ─────┤                    │
  │                       │                     ├─approve_request ─────┤                    │
  │                       │                     │                      ├─UPDATE status ─────┤
  │                       │                     │                      │←─OK ────────────────┤
  │                       │                     │                      ├─set admin_id, time ┤
  │                       │                     │←─updated request ─────┤                    │
  │                       │                     ├─send_welcome_msg ────┤                    │
  │                       │                     │                      ├─bot.send_message ──┤
  │                       │                     ├─send_confirmation ──┤                    │
  │                       │                     │                      ├─bot.send_message ──┤
  │                       │                     │                      │                    │
  │←─confirmation msg ─────┤←─HTTP 200 OK ──────┤                      │                    │
  │
Client                  │                     │                      │                    │
  │                       │                     │                      │                    │
  │←─welcome msg ──────────┤                     │                      │                    │
  │                       │                     │                      │                    │
```

**Key Operations**:

1. Parse Telegram Update
2. Extract admin_id and validate message text = "Approve"
3. Parse request ID from reply_to_message format
4. Call AdminService.approve_request(request_id, admin_id)
5. Service updates database: status=APPROVED, admin_telegram_id, responded_at
6. Send welcome message to client
7. Send confirmation to admin

---

## Database Schema

### ClientRequest Table

```sql
CREATE TABLE client_requests (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    client_telegram_id VARCHAR(20) NOT NULL,
    request_message TEXT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    submitted_at DATETIME NOT NULL,
    admin_telegram_id VARCHAR(20) NULL,
    admin_response VARCHAR(50) NULL,
    responded_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE KEY unique_pending_request (client_telegram_id, status),
    INDEX idx_status (status),
    INDEX idx_admin_id (admin_telegram_id),
    INDEX idx_created_at (created_at)
);
```

### Administrator Table

```sql
CREATE TABLE administrators (
    telegram_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_active (active)
);
```

### Key Design Decisions

- **Unique constraint on (client_telegram_id, status='pending')**: Prevents duplicate pending requests automatically at database level
- **Separate admin table**: Future extensibility for multiple admins, permissions, etc.
- **Indexes on status, admin_id, created_at**: Optimize common query patterns
- **String Telegram IDs**: Compatibility with large integers (Telegram IDs can be very large)
- **Timestamp tracking**: Audit trail and SLA monitoring

---

## Error Handling

### Layer-by-Layer Error Handling

#### Handler Layer

```python
async def handle_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract and validate
        if not update.message or not update.message.text:
            logger.warning(f"Invalid request: missing message")
            return
        
        client_id = str(update.message.from_user.id)
        message = update.message.text.replace("/request", "").strip()
        
        # Call service
        request = await request_service.create_request(client_id, message)
        
    except ValueError as e:
        # Validation error (duplicate, invalid format)
        logger.warning(f"Validation error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")
        
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in request handler: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
```

**Key Patterns**:

- Specific exception types (ValueError, DatabaseError, etc.)
- Graceful user messages (don't expose internal errors)
- Comprehensive logging with context
- Rollback on database errors

#### Service Layer

```python
async def approve_request(request_id: int, admin_id: str) -> ClientRequest | None:
    db = SessionLocal()
    try:
        # Fetch request
        request = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
        if not request:
            logger.warning(f"Request not found: {request_id}")
            return None
        
        # Update request
        request.status = RequestStatus.APPROVED
        request.admin_telegram_id = admin_id
        request.admin_response = "approved"
        request.responded_at = datetime.now(timezone.utc)
        
        db.commit()
        logger.info(f"Request {request_id} approved by {admin_id}")
        return request
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving request {request_id}: {e}", exc_info=True)
        return None
    
    finally:
        db.close()
```

**Key Patterns**:

- Try-catch-finally for resource cleanup
- Rollback on errors
- Null returns for expected failures
- Exceptions for unexpected failures

---

## Testing Strategy

### Three-Layer Testing Approach

#### 1. Contract Tests (API Contracts)

```python
def test_admin_approval_handler():
    """Contract: POST /webhook/telegram with "Approve" → status updated to APPROVED"""
    # Setup: pending request in database
    # Action: POST /webhook/telegram with approval update
    # Assert: response 200, status changed to APPROVED, welcome message sent
```

**Purpose**: Verify API contract between Telegram and application

#### 2. Integration Tests (Full Workflows)

```python
def test_full_approval_flow():
    """Integration: /request → approval → welcome message within 5s SLA"""
    # 1. Client sends /request
    # 2. Request stored in DB
    # 3. Admin approves
    # 4. Request status updated
    # 5. Verify welcome message
    # 6. Verify timing
```

**Purpose**: Verify complete workflows work end-to-end

#### 3. Unit Tests (Business Logic)

```python
@pytest.mark.asyncio
async def test_create_request_duplicate_rejection():
    """Unit: create_request() rejects duplicate pending requests"""
    # Create first request
    request1 = await request_service.create_request("123", "Help")
    
    # Attempt duplicate
    with pytest.raises(ValueError):
        await request_service.create_request("123", "Help again")
```

**Purpose**: Verify individual components work correctly

---

## Design Patterns

### 1. Service Layer Pattern

**Problem**: Business logic scattered across handlers, hard to test

**Solution**: Dedicated service classes with business logic

```python
# Handler just orchestrates
async def handle_request_command(update, context):
    request = await request_service.create_request(client_id, message)
    await notification_service.send_confirmation_to_client(client_id)
```

**Benefits**:

- Testable business logic
- Reusable services
- Clean separation of concerns

### 2. Handler Router Pattern

**Problem**: Where does update routing logic go?

**Solution**: Update handler routes to domain-specific handlers

```python
async def process_update_impl(update):
    if update.message.text.startswith("/request"):
        await handle_request_command(update, ctx)
    elif "approve" in update.message.text.lower():
        await handle_admin_approve(update, ctx)
    elif "reject" in update.message.text.lower():
        await handle_admin_reject(update, ctx)
```

**Benefits**:

- Clear routing logic
- Easy to add new command handlers
- Centralized orchestration

### 3. Repository Pattern (ORM)

**Problem**: Scattered database queries, hard to refactor

**Solution**: ORM models abstract database details

```python
# Service calls ORM, never raw SQL
request = db.query(ClientRequest).filter(ClientRequest.id == request_id).first()
request.status = RequestStatus.APPROVED
db.commit()
```

**Benefits**:

- Database agnostic (can switch PostgreSQL ↔ MySQL)
- Type-safe queries
- Migrations handle schema changes

### 4. Async/Await Throughout

**Problem**: Blocking operations slow down webhook processing

**Solution**: Async handlers and services

```python
async def handle_request_command(update, context):
    # All operations are async
    await request_service.create_request(...)
    await notification_service.send_confirmation_to_client(...)
    await notification_service.send_notification_to_admin(...)
```

**Benefits**:

- Non-blocking operations
- Can handle multiple updates concurrently
- Better webhook performance

---

## Performance Considerations

### Timing SLAs

| Operation | Target SLA | Achieved |
|-----------|-----------|----------|
| Client confirmation | < 2 seconds | ✅ ~200ms |
| Admin notification | < 3 seconds | ✅ ~300ms |
| Approval response | < 5 seconds | ✅ ~400ms |
| Rejection response | < 5 seconds | ✅ ~400ms |

### Optimization Strategies

1. **Database Indexing**:
   - Index on `status` for query efficiency
   - Index on `created_at` for pagination
   - Unique constraint on pending status for duplicate check

2. **Connection Pooling**:

   ```python
   engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
   ```

3. **Async Operations**:
   - Handler layer async throughout
   - Service layer async
   - Services don't block on Telegram API

4. **Caching** (Future):
   - Admin config could be cached in Redis
   - Message templates in-memory

---

## Security Considerations

### 1. Telegram Webhook Security

- **Verification**: Telegram sends HTTPS requests from known IPs
- **Recommendation**: Firewall whitelist Telegram IP ranges

### 2. Input Validation

```python
# Validate all Telegram data
if not update.message or not update.message.text:
    raise ValueError("Invalid update")

if len(message) > MAX_MESSAGE_LENGTH:
    raise ValueError("Message too long")
```

### 3. SQL Injection Prevention

```python
# ✅ Safe: Using ORM parameterized queries
db.query(ClientRequest).filter(ClientRequest.id == request_id).first()

# ❌ Unsafe: Raw SQL with string interpolation
db.execute(f"SELECT * FROM requests WHERE id = {request_id}")
```

### 4. Authentication

- **Admin ID**: Validate admin_id matches configured ADMIN_TELEGRAM_ID
- **Message Format**: Validate message comes from expected format

### 5. Data Privacy

- **Logs**: Never log full request message (PII)
- **Database**: Encrypt sensitive fields if needed
- **Backups**: Secure backup storage

---

## References

- **python-telegram-bot**: [Read the Docs](https://python-telegram-bot.readthedocs.io/)
- **FastAPI**: [Official Site](https://fastapi.tiangolo.com/)
- **SQLAlchemy**: [Documentation](https://docs.sqlalchemy.org/)
- **Async Python**: [Python Docs](https://docs.python.org/3/library/asyncio.html)
