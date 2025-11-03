# Data model for 001-seamless-telegram-auth

## TelegramUserCandidate

Description: A lightweight record created when an unlinked Telegram user requests access via the Mini App.

Fields:

- id: UUID (PK)
- telegram_id: BIGINT (unique, indexed) — Telegram user id (from initData)
- telegram_username: TEXT (nullable)
- first_name: TEXT (nullable)
- last_name: TEXT (nullable)
- photo_url: TEXT (nullable)
- note: TEXT (nullable) — short free-text provided by the user during request
- status: ENUM("pending","cancelled","processed") — initial: "pending"
- created_at: TIMESTAMP UTC
- updated_at: TIMESTAMP UTC

## SOSenkiUser (existing project user model — extended view)

Note: the project already has a user model. For onboarding we require the following fields to be present or added if missing:

- id: INTEGER (PK)
- username: TEXT (nullable, unique)
- email: TEXT (nullable)
- telegram_id: BIGINT (NOT NULL, unique, indexed) — Telegram identity, required for all users (create-on-accept flow)
- first_name: TEXT (nullable)
- last_name: TEXT (nullable)
- phone: TEXT (nullable)
- roles: JSON (default: ["User"]) — contains "Administrator", "User", etc.
- created_at, updated_at: TIMESTAMP UTC

## AdminAction (audit log for admin decisions)

Fields:

- id: UUID (PK)
- request_id: FK -> TelegramUserCandidate.id
- admin_user_id: FK -> SOSenkiUser.id (must have Administrator role)
- action: ENUM("accept","reject")
- payload: JSONB (for accept: assigned role, created user id etc.)
- comment: TEXT (nullable)
- created_at: TIMESTAMP UTC

Validation & constraints

- `telegram_id` must be unique across SOSenkiUser.telegram_id and TelegramUserCandidate.telegram_id; prevent duplicate candidates for same telegram_id (unique index on TelegramUserCandidate.telegram_id).
- When creating a SOSenkiUser as part of an accept action, check for existing SOSenkiUser with same telegram_id; if exists, return an error `user_already_exists` and abort creation.
- `auth_date` coming from Mini App initData must be recent (e.g., <= 2 minutes by default) — configure threshold as environment var.

State transitions

- TelegramUserCandidate.status:
  - pending -> processed: when admin acts (accept or reject)
  - pending -> cancelled: user withdraws request (out-of-scope for MVP UI but recorded)

Acceptance side-effects

- On Accept (admin action):
  - create a new SOSenkiUser (create-on-accept per spec) with telegram_id populated and assigned role(s) provided by admin.
  - set TelegramUserCandidate.status = "processed" and create AdminAction record.
  - send notification to the Telegram user via bot or via Telegram Web App notification (service `telegram_bot.py` handles messaging).

Indexes

- TelegramUserCandidate: unique index on `telegram_id`
- SOSenkiUser: unique index on `telegram_id` (nullable unique)
