# Research & Technical Decisions: Welcome Mini App for Approved Users# Research & Technical Decisions: Welcome Mini App for Approved Users# Research & Technical Decisions: Welcome Mini App for Approved Users# Research & Technical Decisions: Welcome Mini App for Approved Users# Research & Technical Decisions: Welcome Mini App for Approved Users



**Feature**: 002-welcome-mini-app  

**Date**: 2025-11-05  

**Phase**: 0 (Research & Decisions)**Feature**: 002-welcome-mini-app  



## Overview**Date**: 2025-11-05  



This document captures technical research, clarifications, and design decisions for the Welcome Mini App feature. All NEEDS CLARIFICATION items from the specification have been resolved using informed decisions based on project constitution, industry best practices, and the existing SOSenki architecture. **YAGNI Principle Applied**: Only tables and features explicitly required by the specification are included. No redundant timestamp fields.**Phase**: 0 (Research & Decisions)**Feature**: 002-welcome-mini-app  



---



## 1. Telegram Mini App Technology Stack## Overview**Date**: 2025-11-05  



### Decision: Use Telegram Web App API (Official Platform)



**What was chosen**: Telegram's native Web App API (WebApp JavaScript interface)This document captures technical research, clarifications, and design decisions for the Welcome Mini App feature. All NEEDS CLARIFICATION items from the specification have been resolved using informed decisions based on project constitution, industry best practices, and the existing SOSenki architecture. **YAGNI Principle Applied**: Only tables and features explicitly required by the specification are included.**Phase**: 0 (Research & Decisions)**Feature**: 002-welcome-mini-app**Feature**: 002-welcome-mini-app  



**Rationale**:

- Officially supported and maintained by Telegram

- No additional authentication layer needed (Telegram handles it)---

- Runs natively within Telegram client (no external browser required)

- Access to user context via `window.Telegram.WebApp`

- Built-in security model (origin verification, user isolation)

## 1. Telegram Mini App Technology Stack## Overview**Date**: 2025-11-05**Date**: 2025-11-05  

**Alternatives considered**:

- Custom iframe solution: Rejected—adds authentication complexity, less secure

- Native mobile apps (iOS/Swift, Android/Kotlin): Rejected—violates YAGNI

- Progressive Web App (PWA): Rejected—requires service workers, offline support not needed### Decision: Use Telegram Web App API (Official Platform)



**Implementation approach**:

- Backend serves Mini App HTML/CSS/JavaScript from FastAPI

- Client-side JS uses `window.Telegram.WebApp` API to identify user**What was chosen**: Telegram's native Web App API (WebApp JavaScript interface)This document captures technical research, clarifications, and design decisions for the Welcome Mini App feature. All NEEDS CLARIFICATION items from the specification have been resolved using informed decisions based on project constitution, industry best practices, and the existing SOSenki architecture.**Phase**: 0 (Research & Decisions)**Phase**: 0 (Research & Decisions)

- Backend verifies user via Telegram signature validation



---

**Rationale**:

## 2. Registration Verification Strategy

- Officially supported and maintained by Telegram

### Decision: Database Query at Mini App Load + Local Caching

- No additional authentication layer needed (Telegram handles it)---

**What was chosen**: 

- On Mini App load, query SQLite database to check user's approval status- Runs natively within Telegram client (no external browser required)

- Check User.is_active flag (primary access gate)

- Cache result in browser session storage for 5 minutes- Access to user context via `window.Telegram.WebApp`

- Re-verify on page refresh or cache expiration

- Built-in security model (origin verification, user isolation)

**Rationale**:

- Simple, deterministic: single source of truth is database## 1. Telegram Mini App Technology Stack## Overview## Overview

- Atomic: no race conditions between approval and Mini App access

- Transparent: audit trail maintained via AccessRequest records**Alternatives considered**:

- Meets performance target (<3 seconds load time)

- Aligns with SQLite usage per constitution- Custom iframe solution: Rejected—adds authentication complexity, less secure



**Alternatives considered**:- Native mobile apps (iOS/Swift, Android/Kotlin): Rejected—violates YAGNI (requires duplicate codebases), scope exceeds MVP

- Redis caching layer: Rejected—violates YAGNI

- Token-based approach (JWT): Rejected—requires refresh logic- Progressive Web App (PWA): Rejected—requires service workers, offline support not needed for MVP### Decision: Use Telegram Web App API (Official Platform)

- Webhook polling: Rejected—unnecessary



**Implementation details**:

- Endpoint: `GET /api/mini-app/init` returns `{ isRegistered: boolean, userName?: string }`**Implementation approach**:

- Response time: <100ms for SQLite query

- Cache: Browser session storage, cleared on tab close- Backend serves Mini App HTML/CSS/JavaScript from FastAPI static files



---- Client-side JS uses `window.Telegram.WebApp` API to identify user**What was chosen**: Telegram's native Web App API (WebApp JavaScript interface)This document captures technical research, clarifications, and design decisions for the Welcome Mini App feature. All NEEDS CLARIFICATION items from the specification have been resolved using informed decisions based on project constitution, industry best practices, and the existing SOSenki architecture.This document captures technical research, clarifications, and design decisions for the Welcome Mini App feature. All NEEDS CLARIFICATION items from the specification have been resolved using informed decisions based on project constitution, industry best practices, and the existing SOSenki architecture.



## 3. Mini App Frontend Architecture- Backend verifies user via Telegram user data signature (cryptographic validation)



### Decision: Plain HTML/CSS/JavaScript (No Framework)



**What was chosen**: ---

- Vanilla JavaScript (no React, Vue, Svelte)

- CSS Grid for layout**Rationale**:

- Inline styles for nature-inspired colors

## 2. Registration Verification Strategy

**Rationale**:

- Minimizes bundle size (no build pipeline)- Officially supported and maintained by Telegram

- Meets KISS principle (simple, maintainable)

- No Node.js build tools needed### Decision: Database Query at Mini App Load + Local Caching

- Faster initial load time

- No additional authentication layer needed (Telegram handles it)------

**Alternatives considered**:

- React/TypeScript: Rejected—build complexity, violates YAGNI**What was chosen**: 

- Vue.js: Rejected—same concerns as React

- Web Components: Rejected—overkill for menu display- On Mini App load, query SQLite database to check if user's Telegram ID is approved- Runs natively within Telegram client (no external browser required)



---- Cache result locally in browser session storage for 5 minutes



## 4. Approval Notification Delivery- Re-verify on page refresh or cache expiration- Access to user context via `window.Telegram.WebApp`



### Decision: Extend 001-request-approval Webhook (No Separate Message)



**What was chosen**:**Rationale**:- Built-in security model (origin verification, user isolation)

- Welcome notification already sent by 001-request-approval webhook upon approval

- Mini App link included in that Welcome message- Simple, deterministic: single source of truth is the database

- **No separate ApprovalNotification table** - violates YAGNI

- Atomic: no race conditions between approval and Mini App access## 1. Telegram Mini App Technology Stack## 1. Telegram Mini App Technology Stack

**Rationale**:

- Reuses existing notification mechanism- Transparent: audit trail maintained via AccessRequest records

- Audit trail maintained via AccessRequest records

- Meets <5 second delivery target- Meets performance target (<3 seconds load time)**Alternatives considered**:

- Simpler architecture

- Aligns with SQLite usage per constitution

**Clarification**:

- "We don't send separate Welcome message to MiniApp - it's just a link in Welcome message already implemented in 001 feature"- Custom iframe solution: Rejected—adds authentication complexity, less secure

- Redundant timestamp fields removed from AccessRequest (approved_at, mini_app_first_opened_at not needed)

**Alternatives considered**:

---

- Redis caching layer: Rejected—violates YAGNI, adds infrastructure- Native mobile apps (iOS/Swift, Android/Kotlin): Rejected—violates YAGNI (requires duplicate codebases), scope exceeds MVP

## 5. Design System: Color Palette & Styling

- Token-based approach (JWT): Rejected—requires token refresh logic

### Decision: CSS Variables + Apple Design Principles

- Webhook polling: Rejected—unnecessary, SQLite query is instant- Progressive Web App (PWA): Rejected—requires service workers, offline support not needed for MVP### Decision: Use Telegram Web App API (Official Platform)### Decision: Use Telegram Web App API (Official Platform)

**What was chosen**:

- Nature-inspired colors as CSS custom properties (pine, water, sand)

- Apple design principles: clean whitespace, readable typography

- CSS Grid for responsive layout (mobile-first)**Implementation details**:

- No external CSS framework

- Endpoint: `GET /api/mini-app/init` returns `{ isRegistered: boolean, userName?: string }`

**Color definitions**:

```css- Response time: <100ms for SQLite query**Implementation approach**:

:root {

  --color-pine: #2D5016;      /* Forest green */- Cache: Browser session storage, cleared on tab close

  --color-water: #0099CC;     /* Aqua/teal */

  --color-sand: #D4A574;      /* Beige */- Backend serves Mini App HTML/CSS/JavaScript from FastAPI static files or template endpoint

}

```---



**Rationale**:- Client-side JS uses `window.Telegram.WebApp` API to identify user**What was chosen**: Telegram's native Web App API (WebApp JavaScript interface)**What was chosen**: Telegram's native Web App API (WebApp JavaScript interface)

- Nature palette is cohesive and calming

- CSS variables enable consistent theming## 3. Mini App Frontend Architecture

- Meets accessibility standards (WCAG AA)

- Backend verifies user via Telegram user data signature (cryptographic validation)

---

### Decision: Plain HTML/CSS/JavaScript (No Framework)

## 6. Mini App API Endpoints



### Decision: RESTful JSON API

**What was chosen**: 

**What was chosen**:

- `GET /api/mini-app/init` - Initialization (status + menu)- Vanilla JavaScript (no React, Vue, Svelte)---

- `GET /api/mini-app/verify-registration` - Verify current user

- `POST /api/mini-app/menu-action` - Placeholder for future- CSS Grid for layout



**Rationale**:- Inline styles for nature-inspired colors**Rationale**:**Rationale**:

- RESTful convention aligns with FastAPI

- JSON responses simple and universal

- No GraphQL complexity

**Rationale**:## 2. Registration Verification Strategy

---

- Minimizes bundle size (no build pipeline, faster load)

## 7. Error Handling & Fallback UX

- Meets KISS principle (simple to read, maintain, debug)

### Decision: Graceful Degradation

- No dependency on Node.js build tools

**What was chosen**:

- Network errors: Display retry button + error message- Faster initial load time### Decision: Database Query at Mini App Load + Local Caching

- Invalid Telegram ID: Display "Unexpected error. Please restart the app."

- Verification timeout: Auto-retry up to 2 times

- Menu not implemented: Display "Coming soon"

**Alternatives considered**:- Officially supported and maintained by Telegram- Officially supported and maintained by Telegram

**Rationale**:

- Prevents blank screens- React/TypeScript: Rejected—build complexity, transpilation overhead, violates YAGNI

- Clear user communication

- Retry logic handles transient failures- Vue.js: Rejected—same concerns as React**What was chosen**: 



---- Web Components: Rejected—overkill for simple menu display



## 8. User Model Architecture: Flexible Access Control- On Mini App load, query SQLite database to check if user's Telegram ID exists in approved users- No additional authentication layer needed (Telegram handles it)- No additional authentication layer needed (Telegram handles it)



### Decision: Boolean Role Flags with Primary Access Gate---



**What was chosen**:- Cache result locally in browser session storage for 5 minutes (configurable)

- `is_active` (Boolean) = **PRIMARY Mini App access gate** for ALL users

- Feature-level flags: `is_investor` (can access Invest features), `is_administrator`, `is_owner`, `is_staff`## 4. Approval Notification Delivery

- Users can hold multiple roles simultaneously

- AccessRequest renamed from ClientRequest (serves as audit log)- Re-verify on page refresh or cache expiration- Runs natively within Telegram client- Runs natively within Telegram client (no external browser required)



**Rationale**:### Decision: Extend 001-request-approval Webhook (No Separate Message)

- YAGNI: `is_active` is simple, universal access gate

- Mini App access = is_active (True/False)

- Feature access = role flags (is_investor, etc.)

- Scales to future features without schema changes**What was chosen**:

- Users can be Admin AND Investor simultaneously

- Welcome notification is already sent by 001-request-approval webhook upon approval**Rationale**:- Access to user context via `window.Telegram.WebApp`- Access to user context via `window.Telegram.WebApp`

**User states**:

- Not approved: `is_active=False` (cannot access Mini App)- Mini App link is included in that Welcome message

- Approved: `is_active=True` (can access Mini App)

- Investor: `is_investor=True, is_active=True` (can access Invest features)- **No separate ApprovalNotification table** - violates YAGNI- Simple, deterministic: single source of truth is the database

- Administrator: `is_administrator=True, is_active=True` (can approve requests)

- Admin + Investor: `is_administrator=True, is_investor=True, is_active=True`

- Deactivated: `is_active=False` (preserves all role flags for audit trail)

**Rationale**:- Atomic: no race conditions between approval and Mini App access- Built-in security model (origin verification, user isolation)- Built-in security model (origin verification, user isolation)

**Why is_active is the primary gate**:

- Single boolean check for all features- Reuses existing notification mechanism (no duplication)

- Soft-delete pattern (never hard-delete)

- Clear permission semantics- Audit trail maintained via AccessRequest records (immutable)- Transparent: audit trail maintained (registration timestamp, approval timestamp)

- No role hierarchy complexity

- Meets <5 second delivery target (handled by 001 feature)

**Alternatives rejected**:

- Role enum: Violates requirement for simultaneous roles- Simpler architecture, fewer tables- Meets performance target (<3 seconds load time)

- Role table with many-to-many: Over-engineered for MVP

- String roles: Allows typos, harder to validate



**AccessRequest fields removed** (per YAGNI):**Clarification**:- Aligns with SQLite usage per constitution

- ~~`approved_at`~~ → Use `responded_at` instead (already present)

- ~~`mini_app_first_opened_at`~~ → Not required by specification, no audit benefit- User explicitly stated: "We don't send separate Welcome message to MiniApp - it's just a link in Welcome message already implemented in 001 feature"



**Future Extensions** (work with this base without schema changes):- This eliminates ApprovalNotification table from data model per YAGNI**Alternatives considered**:**Alternatives considered**:

- Permission matrix (fine-grained role permissions)

- Role hierarchies or groups

- User preferences/settings

- Activity/audit logging---**Alternatives considered**:



---



## 9. Security Considerations## 5. Design System: Color Palette & Styling- Redis caching layer: Rejected—violates YAGNI, adds infrastructure complexity not needed for MVP



### Decision: Verify Telegram User Data Signature



**What was chosen**:### Decision: CSS Variables + Apple Design Principles- Token-based approach (JWT issued at approval): Rejected—requires token refresh logic, more complex state management

- Verify `initData` from Telegram WebApp API using bot token (HMAC-SHA256)

- Check `auth_date` to prevent replay attacks (±5 min tolerance)

- Extract user.id and user.username only after validation

**What was chosen**:- Webhook polling: Rejected—unnecessary, database query is instant for SQLite- Custom iframe solution: Rejected—adds authentication complexity- Custom iframe solution: Rejected—adds authentication complexity, less secure

**Rationale**:

- Ensures requests are genuinely from Telegram- Nature-inspired colors as CSS custom properties (pine, water, sand)

- Prevents spoofed requests

- Per-request verification (no persistent tokens)- Apple design principles: clean whitespace, readable typography

- Recommended by Telegram official docs

- CSS Grid for responsive layout (mobile-first)

---

- No external CSS framework**Implementation details**:- Native mobile apps (iOS/Swift): Rejected—violates YAGNI- Native mobile apps (iOS/Swift, Android/Kotlin): Rejected—violates YAGNI (requires duplicate codebases), scope exceeds MVP

## 10. Performance & Caching Strategy



### Decision: Multi-Layer Caching

**Color definitions**:- Endpoint: `GET /api/mini-app/verify-registration` returns `{ isRegistered: boolean, userName?: string }`

**What was chosen**:

- Browser session storage: Cache status for 5 minutes```css

- SQLite indexes on: user.telegram_id, access_request.user_telegram_id

- FastAPI caching: Cache /api/mini-app/init for 1 minute per user:root {- Response time: <100ms for SQLite query- Progressive Web App (PWA): Rejected—requires service workers for offline- Progressive Web App (PWA): Rejected—requires service workers, offline support not needed for MVP



**Rationale**:  --color-pine: #2D5016;      /* Forest green */

- Reduces database queries

- Meets <3 second load time target  --color-water: #0099CC;     /* Aqua/teal */- Cache: Browser session storage, cleared on tab close

- Respects data freshness

  --color-sand: #D4A574;      /* Beige */

---

  --color-text: #1a1a1a;      /* Dark gray */- Error handling: If verification fails (network error), display graceful error with retry option

## 11. Mobile Responsiveness

  --color-bg: #f5f5f5;        /* Light background */

### Decision: CSS Media Queries (Mobile-First Design)

  --color-border: #e0e0e0;    /* Subtle borders */

**What was chosen**:

- Base CSS targets mobile (<600px)}

- Media queries expand layout for tablet+ (>600px)

- Touch-friendly tap targets (min 44px height)```---**Implementation**: Backend serves HTML/CSS/JS from FastAPI; client uses `window.Telegram.WebApp` API**Implementation approach**:



**Rationale**:

- Telegram Mini Apps accessed primarily on mobile

- Meets accessibility standards (WCAG)**Rationale**:

- No framework overhead

- Nature palette is cohesive and calming

---

- CSS variables enable consistent theming## 3. Mini App Frontend Architecture

## 12. State Management: Stateless Architecture

- Meets accessibility standards (WCAG AA)

### Decision: Simple Stateless Design

- Apple-inspired design resonates with users

**What was chosen**:

- No complex state machine

- Approval sends notification via 001-request-approval webhook

- User opens Mini App link---### Decision: Plain HTML/CSS/JavaScript (No Framework)---- Backend serves Mini App HTML/CSS/JavaScript from FastAPI static files or template endpoint

- Mini App queries database on load (state on-demand)

- No "confirmation" or "activation" step



**Rationale**:## 6. Mini App API Endpoints

- Minimizes complexity (KISS)

- Database is single source of truth

- Users expect immediate access after approval

### Decision: RESTful JSON API**What was chosen**: - Client-side JS uses `window.Telegram.WebApp` API to identify user

---



## 13. Optional Analytics: MiniAppSession

**What was chosen**:- Vanilla JavaScript (no React, Vue, Svelte, etc.)

### Decision: MiniAppSession Table (Optional per YAGNI)

- `GET /api/mini-app/init` - Initialization (registration status + menu config)

**What was chosen**:

- MiniAppSession table is optional- `GET /api/mini-app/verify-registration` - Verify current user registration- CSS Grid for layout## 2. Registration Verification Strategy- Backend verifies user via Telegram user data signature (cryptographic validation)

- Can be skipped if analytics not needed in MVP

- If implemented: tracks session usage, menu views, errors- `POST /api/mini-app/menu-action` - Placeholder for future menu interactions



**Rationale**:- Inline styles for nature-inspired colors

- Not explicitly required by specification

- Useful for debugging but not critical**Rationale**:

- Can be added later without schema changes

- RESTful convention aligns with FastAPI best practices- Single HTML file or server-rendered template

---

- JSON responses simple and universal

## Clarifications Resolved

- No GraphQL complexity needed for MVP

All NEEDS CLARIFICATION markers from spec addressed:



1. ✅ **User registration status changes** → Cache expiration + re-query

2. ✅ **Invalid Telegram ID handling** → Graceful error + retry---**Rationale**:### Decision: Database Query at Mini App Load + Local Caching---

3. ✅ **Shared link verification** → Per-user verification enforced

4. ✅ **Registration verification** → Database query + Telegram signature

5. ✅ **Mini App failure** → Error message + retry button

## 7. Error Handling & Fallback UX- Minimizes bundle size (no build pipeline, faster load)

---



## YAGNI Principle Application

### Decision: Graceful Degradation- Meets KISS principle (simple to read, maintain, debug)

**Not included in this feature** (deferred to future needs):



- ❌ ApprovalNotification table → Handled by 001-request-approval

- ❌ `approved_at` field → Use `responded_at` instead**What was chosen**:- No dependency on Node.js build tools (aligns with Python backend)

- ❌ `mini_app_first_opened_at` field → Not needed per spec

- ❌ Permission matrix → Simple boolean flags sufficient- Network errors: Display retry button + error message

- ❌ User preferences table → Not needed for MVP

- ✅ MiniAppSession → Optional for analytics (can be deferred)- Invalid Telegram ID: Display "Unexpected error. Please restart the app."- Faster initial load time**What was chosen**:## 2. Registration Verification Strategy



**Why these decisions matter**:- Verification timeout: Auto-retry up to 2 times

- Smaller database schema → Faster migrations

- Fewer dependencies → Lower maintenance- Menu not implemented: Display "Coming soon" placeholder- Nature-inspired color palette defined as CSS variables

- Cleaner code → Easier to understand

- Faster delivery → Focus on core functionality



---**Rationale**:



## Next Steps- Prevents blank screens (poor UX)



1. Approve data-model.md (YAGNI-compliant)- Clear user communication**Alternatives considered**:

2. Create API contracts in contracts/mini-app-api.md

3. Update quickstart.md with corrected User model- Retry logic handles transient failures

4. Execute /speckit.tasks to generate Phase 2 tasks

- React/TypeScript: Rejected—build complexity, transpilation overhead, violates YAGNI- Query SQLite database at Mini App load to check Telegram ID in approved users### Decision: Database Query at Mini App Load + Local Caching

---

- Vue.js: Rejected—same concerns as React

## 8. User Model Architecture: Multiple Roles Support

- Web Components: Rejected—overkill for simple menu display- Cache result in browser session storage for 5 minutes

### Decision: Multiple Independent Boolean Role Flags



**What was chosen**:

- User table with independent boolean flags: `is_client`, `is_administrator`, `is_owner`, `is_staff`**Implementation approach**:- Re-verify on page refresh or cache expiration**What was chosen**: 

- Users can hold multiple roles simultaneously

- **Not a single role enum** - allows flexible combinations```html



**Rationale**:<!-- src/static/mini_app/index.html -->- On Mini App load, query SQLite database to check if user's Telegram ID exists in approved users

- User can be Administrator AND Owner AND Staff at the same time

- Simpler than role hierarchy or intermediate tables<html>

- Scales to future roles without schema changes

- YAGNI: Only implemented what's needed (no permission matrix yet)  <head>**Rationale**:- Cache result locally in browser session storage for 5 minutes (configurable)



**User states**:    <style>

- Client pending approval: `is_client=False, is_active=False`

- Approved client: `is_client=True, is_active=True`      :root {- Re-verify on page refresh or cache expiration

- Administrator: `is_administrator=True, is_active=True`

- Admin + Owner: `is_administrator=True, is_owner=True, is_active=True`        --color-pine: #2D5016;    /* Forest green */

- Deactivated: `is_active=False` (preserves all role flags for audit trail)

        --color-water: #0099CC;   /* Aqua/teal */- Simple, deterministic: single source of truth

**Alternatives rejected**:

- Single role enum (client/admin/staff): Violates requirement that user can be multiple roles simultaneously        --color-sand: #D4A574;    /* Beige */

- Role table with many-to-many: Over-engineered for MVP

- String roles without validation: Allows typos, harder to enforce      }- Atomic: no race conditions**Rationale**:



**Future Extensions** (work with this base without schema changes):      body { /* Clean, minimalistic layout */ }

- Permission matrix (fine-grained role permissions)

- Role groups/hierarchies    </style>- Transparent: audit trail maintained- Simple, deterministic: single source of truth is the database

- Audit logging of role changes

  </head>

---

  <body>- Meets <3 seconds load performance target- Atomic: no race conditions between approval and Mini App access

## 9. Security Considerations

    <div id="app">

### Decision: Verify Telegram User Data Signature

      <!-- Will be populated by app.js -->- Aligns with SQLite usage per constitution- Transparent: audit trail maintained (registration timestamp, approval timestamp)

**What was chosen**:

- Verify `initData` from Telegram WebApp API using bot token (HMAC-SHA256)    </div>

- Check `auth_date` to prevent replay attacks (±5 minute tolerance)

- Extract `user.id` and `user.username` only after validation    <script src="app.js"></script>- Meets performance target (<3 seconds load time)



**Rationale**:  </body>

- Ensures requests are genuinely from Telegram

- Prevents spoofed requests</html>**Alternatives considered**:- Aligns with SQLite usage per constitution

- Per-request verification (no persistent tokens)

- Recommended by Telegram official docs```



---



## 10. Performance & Caching Strategy---



### Decision: Multi-Layer Caching- Redis caching: Rejected—violates YAGNI**Alternatives considered**:



**What was chosen**:## 4. Approval Notification Delivery

- Browser session storage: Cache registration status for 5 minutes

- SQLite indexes on: `user.telegram_id`, `access_request.user_telegram_id`- JWT tokens: Rejected—requires refresh logic- Redis caching layer: Rejected—violates YAGNI, adds infrastructure complexity not needed for MVP

- FastAPI caching: Cache `/api/mini-app/init` response for 1 minute per user

### Decision: Extend 001-request-approval Webhook + Send Message

**Rationale**:

- Reduces database queries- Webhook polling: Rejected—unnecessary complexity- Token-based approach (JWT issued at approval): Rejected—requires token refresh logic, more complex state management

- Meets <3 second load time target

- Respects data freshness**What was chosen**:



---- On approval, existing webhook handler in 001-request-approval processes admin response- Webhook polling: Rejected—unnecessary, database query is instant for SQLite



## 11. Mobile Responsiveness- Approval handler triggers new `approval_service.send_welcome_notification()`



### Decision: CSS Media Queries (Mobile-First Design)- Notification includes text + inline button linking to Mini App deeplink**Implementation**: `GET /api/mini-app/verify-registration` returns `{ isRegistered: boolean, userName?: string }`



**What was chosen**:

- Base CSS targets mobile (<600px)

- Media queries expand layout for tablet+ (>600px)**Rationale**:**Implementation details**:

- Touch-friendly tap targets (min 44px height)

- Builds on existing bot infrastructure (no new external services)

**Rationale**:

- Telegram Mini Apps accessed primarily on mobile- Leverages python-telegram-bot library (already used)---- Endpoint: `GET /api/mini-app/verify-registration` returns `{ isRegistered: boolean, userName?: string }`

- Meets accessibility standards (WCAG)

- No framework overhead- Inline buttons are native Telegram feature (good UX)



---- Meets <5 second delivery target- Response time: <100ms for SQLite query



## 12. State Management: Stateless Architecture



### Decision: Simple Stateless Design**Alternatives considered**:## 3. Mini App Frontend Architecture- Cache: Browser session storage, cleared on tab close



**What was chosen**:- Message queue (Celery): Rejected—violates YAGNI, adds infrastructure

- No complex state machine

- Approval sends notification via 001-request-approval webhook- Scheduled task: Rejected—notification should be immediate on approval- Error handling: If verification fails (network error), display graceful error with retry option

- User opens Mini App link

- Mini App queries database on load (state fetched on-demand)- Email/SMS: Explicitly out of scope (Telegram only)

- No "confirmation" or "activation" step

### Decision: Plain HTML/CSS/JavaScript (No Framework)

**Rationale**:

- Minimizes complexity (KISS)**Implementation details**:

- Database is single source of truth

- Users expect immediate access after approval- Endpoint: Approval response parsed from Telegram callback query---



---- Button deeplink format: `https://t.me/[BOT_NAME]/[MINI_APP_ID]?startapp=approved`



## 13. Optional Analytics: MiniAppSession- Message template: "✅ Access granted! Open the SOSenki app to get started → [Open App]"**What was chosen**:



### Decision: MiniAppSession Table (Optional per YAGNI)



**What was chosen**:---## 3. Mini App Frontend Architecture

- MiniAppSession table is optional

- Can be skipped if analytics not needed in MVP

- If implemented: tracks session usage, menu views, errors

## 5. Design System: Color Palette & Styling- Vanilla JavaScript (no React, Vue, Svelte)

**Rationale**:

- Not explicitly required by specification

- Useful for debugging but not critical

- Can be added later without schema changes### Decision: CSS Variables + Apple Design Principles- CSS Grid for layout### Decision: Plain HTML/CSS/JavaScript (No Framework)

- Follow YAGNI: only if analytics explicitly requested



---

**What was chosen**:- Inline styles for nature-inspired colors

## Clarifications Resolved

- Define nature-inspired colors as CSS custom properties

All NEEDS CLARIFICATION markers from spec addressed:

- Apply Apple design principles: clean whitespace, readable typography, subtle shadows- Single HTML file or server-rendered template**What was chosen**: 

1. ✅ **User registration status changes** → Cache expiration + re-query on refresh

2. ✅ **Invalid Telegram ID handling** → Graceful error display + retry- Use CSS Grid for responsive layout (single column for mobile, adjustable for tablet)

3. ✅ **Shared link from approved user** → Mini App enforces per-user verification

4. ✅ **Registration verification** → Database query + Telegram signature validation- No external CSS framework (Bootstrap, Tailwind rejected per KISS)- Vanilla JavaScript (no React, Vue, Svelte, etc.)

5. ✅ **Mini App failure** → Error message + retry button



---

**Color definitions** (with hex codes):**Rationale**:- CSS Grid for layout

## YAGNI Principle Application

```css

**Not included in this feature** (deferred to future needs):

:root {- Inline styles for nature-inspired colors

- ❌ ApprovalNotification table → Welcome message already sent via 001-request-approval

- ❌ Permission matrix → Roles are simple boolean flags  --color-pine: #2D5016;      /* Forest green (primary accent) */

- ❌ User preferences table → Not needed for MVP

- ❌ Device tracking → Not needed for MVP  --color-water: #0099CC;     /* Aqua/teal (secondary accent) */- Minimizes bundle size (no build pipeline)- Single HTML file or server-rendered template

- ✅ MiniAppSession → Optional for analytics (can be deferred)

  --color-sand: #D4A574;      /* Beige (neutral accent, warm) */

**Why these decisions matter**:

- Smaller database schema → Faster migrations, simpler backups  --color-text: #1a1a1a;      /* Dark gray for text */- Meets KISS principle

- Fewer dependencies → Lower maintenance burden

- Cleaner code → Easier to understand and modify  --color-bg: #f5f5f5;        /* Light background */

- Faster feature delivery → Focus on core functionality first

  --color-border: #e0e0e0;    /* Subtle borders */- No dependency on Node.js build tools**Rationale**:

---

}

## Next Steps

```- Faster initial load time- Minimizes bundle size (no build pipeline, faster load)

1. Approve data-model.md (now YAGNI-compliant)

2. Create API contracts in `contracts/mini-app-api.md`

3. Update quickstart.md with corrected User model

4. Execute /speckit.tasks to generate Phase 2 implementation tasks**Rationale**:- Meets KISS principle (simple to read, maintain, debug)


- Nature palette is cohesive and calming

- CSS variables enable consistent theming**Alternatives considered**:- No dependency on Node.js build tools (aligns with Python backend)

- Meets accessibility standards (WCAG AA contrast ratios)

- Apple-inspired: sans-serif font, generous padding, minimal decorations- Faster initial load time



**Alternatives considered**:- React/TypeScript: Rejected—build complexity, violates YAGNI- Nature-inspired color palette defined as CSS variables

- Custom color scheme per user: Rejected—MVP doesn't require theming complexity

- Material Design palette: Rejected—contradicts Apple design target specified in feature- Vue.js: Rejected—same concerns

- Dark mode: Explicitly out of scope for MVP

- Web Components: Rejected—overkill**Alternatives considered**:

---

- React/TypeScript: Rejected—build complexity, transpilation overhead, violates YAGNI

## 6. Mini App API Endpoints

**Implementation**: Plain HTML with CSS variables for color theming- Vue.js: Rejected—same concerns as React

### Decision: RESTful JSON API

- Web Components: Rejected—overkill for simple menu display

**What was chosen**:

- `GET /api/mini-app/init` - Initialization endpoint (returns user registration status + menu config)---

- `GET /api/mini-app/verify-registration` - Verify current user's registration (for cache refresh)

- `POST /api/mini-app/menu-action` - Placeholder for future menu interactions (Rule, Pay, Invest)**Implementation approach**:



**Rationale**:## 4. Approval Notification Delivery```html

- RESTful convention aligns with FastAPI best practices

- JSON responses simple and universal<!-- src/static/mini_app/index.html -->

- No GraphQL complexity for this MVP

- Contracts can be specified as OpenAPI schema### Decision: Extend 001-request-approval Webhook + Send Message<html>



**Alternatives considered**:  <head>

- GraphQL: Rejected—overkill for 2-3 simple queries

- WebSockets: Rejected—no real-time updates needed**What was chosen**:    <style>

- gRPC: Rejected—added complexity, not needed for web-based Mini App

      :root {

---

- On approval, webhook handler processes admin response        --color-pine: #2D5016;    /* Forest green */

## 7. Error Handling & Fallback UX

- Triggers `approval_service.send_welcome_notification()`        --color-water: #0099CC;   /* Aqua/teal */

### Decision: Graceful Degradation

- Notification includes button linking to Mini App deeplink        --color-sand: #D4A574;    /* Beige */

**What was chosen**:

- Network errors: Display retry button + error message (e.g., "Unable to load. Check connection and try again.")      }

- Invalid Telegram ID: Display "Unexpected error. Please restart the app."

- Registration verification timeout (>3 seconds): Auto-retry up to 2 times, then show error**Rationale**:      body { /* Clean, minimalistic layout */ }

- Menu item not implemented: Display "Coming soon" placeholder message

    </style>

**Rationale**:

- Prevents blank screens (bad UX)- Builds on existing bot infrastructure  </head>

- Clear user communication (why something failed)

- No technical jargon (non-technical users)- Leverages python-telegram-bot library  <body>

- Retry logic handles transient failures

- Inline buttons are native Telegram feature    <div id="app">

**Alternatives considered**:

- Silent failures with logging: Rejected—poor UX, users confused- Meets <5 second delivery target      <!-- Will be populated by app.js -->

- Error codes: Rejected—non-technical users won't understand

- Automatic reload: Rejected—confusing, risk of infinite loops    </div>



---**Alternatives considered**:    <script src="app.js"></script>



## 8. User Model Architecture: Unified Role-Based Design  </body>



### Decision: Unified User Model with Role-Based Access Control- Message queue (Celery): Rejected—violates YAGNI</html>



**What was chosen**:- Scheduled task: Rejected—notification should be immediate```

- Single unified `User` table (consolidates 001-request-approval Administrator with 002-welcome-mini-app Client concept)

- `User` model with role field (ENUM: client/administrator/staff)

- Rename `ClientRequest` → `AccessRequest` for semantic clarity

- Merge separate `Administrator` model into `User` with role='administrator'**Implementation**: Button deeplink format: `https://t.me/[BOT_NAME]/[MINI_APP_ID]?startapp=approved`---

- Maintain referential integrity: `AccessRequest.user_telegram_id` → `User.telegram_id`



**Rationale**:

- YAGNI: Role enum (client/administrator/staff) enables future permission systems without schema redesigns---## 4. Approval Notification Delivery

- Audit Trail: Soft-delete pattern (is_active flag) preserves all historical data; never delete User records

- Consistency: All user-related data (telegram_id, username, first_name, last_name, role, is_active, timestamps) unified in one place

- Scalability: Support staff roles, moderators, or service accounts without schema migration

- Better semantics: AccessRequest clarifies that we're tracking access approvals, not just "client requests"## 5. Design System: Color Palette & Styling### Decision: Extend 001-request-approval Webhook + Send Message



**Role semantics**:

- 'client': Regular user requesting access, can view Mini App after approval

- 'administrator': Approves/rejects access requests, can manage client roster### Decision: CSS Variables + Apple Design Principles**What was chosen**:

- 'staff': Future extension for support team, can view analytics but not approve

- On approval, existing webhook handler in 001-request-approval processes admin response

**Migration from 001-request-approval**:

- Import existing Administrator entries (from admin_config.py) as User with role='administrator'**What was chosen**:- Approval handler triggers new `approval_service.send_welcome_notification()`

- Approved ClientRequests create User entries with role='client'

- ClientRequest becomes AccessRequest (renamed, maintains approval history)- Notification includes text + inline button linking to Mini App deeplink



**Access Control**:- Nature-inspired colors as CSS custom properties

- Mini App access: User.role='client' AND User.is_active=true AND AccessRequest.status='approved'

- Admin dashboard: User.role IN ('administrator', 'staff') AND User.is_active=true- Apple design principles: clean whitespace, readable typography**Rationale**:

- Deactivation: Set is_active=false instead of deleting (preserves audit trail)

- CSS Grid for responsive layout- Builds on existing bot infrastructure (no new external services)

**Alternatives considered**:

- Separate RegisteredUser + Administrator tables: Violates YAGNI, complicates queries, duplicates schema- No external CSS framework- Leverages python-telegram-bot library (already used)

- Database inheritance/polymorphism: Overcomplicates for 3-role scheme, vendor-specific

- String roles without enum: Allows typos, harder to validate, no IDE support- Inline buttons are native Telegram feature (good UX)

- Separate User service vs Admin service: Creates duplicate code, conflicting business logic

**Color definitions**:- Meets <5 second delivery target

**Future Extensions** (all work with this base model without schema changes):

- Permission matrix (which roles can do what actions)

- User preferences (notification settings, UI theme)

- Group memberships (departments, organizations)- Pine: #2D5016 (forest green, primary)**Alternatives considered**:

- Activity logging (tracks who did what, when)

- Water: #0099CC (aqua, secondary)- Message queue (Celery): Rejected—violates YAGNI, adds infrastructure

---

- Sand: #D4A574 (beige, neutral warm accent)- Scheduled task: Rejected—notification should be immediate on approval

## 9. Security Considerations

- Email/SMS: Explicitly out of scope (Telegram only)

### Decision: Verify Telegram User Data Signature

**Rationale**:

**What was chosen**:

- On Mini App backend initialization, verify the `initData` passed from Telegram WebApp API**Implementation details**:

- Validate signature using bot token (cryptographic HMAC-SHA256 check)

- Check `auth_date` to prevent replay attacks (tolerance: ±5 minutes)- Cohesive, calming nature palette- Endpoint: Approval response parsed from Telegram callback query

- Extract `user.id` and `user.username` only after validation

- Meets accessibility standards (WCAG AA)- Button deeplink format: `https://t.me/[BOT_NAME]/[MINI_APP_ID]?startapp=approved`

**Rationale**:

- Ensures requests are genuinely from Telegram- Enables consistent theming via CSS variables- Message template: "✅ Access granted! Open the SOSenki app to get started → [Open App]"

- Prevents spoofed requests with arbitrary user IDs

- Per-request verification (no persistent tokens)

- Recommended by Telegram official docs

**Alternatives considered**:---

**Alternatives considered**:

- Trust Telegram context implicitly: Rejected—security risk, not following OAuth best practices

- JWT token issued by server: Rejected—added complexity, Telegram's built-in mechanism is sufficient

- Custom color per user: Rejected—MVP doesn't require theming## 5. Design System: Color Palette & Styling

---

- Material Design: Rejected—contradicts Apple design target

## 10. Performance & Caching Strategy

### Decision: CSS Variables + Apple Design Principles

### Decision: Multi-Layer Caching

---

**What was chosen**:

- Browser session storage: Cache registration status for 5 minutes**What was chosen**:

- SQLite query optimization: Index on `user.telegram_id` and `access_request.user_telegram_id`

- FastAPI response caching: Cache `/api/mini-app/init` for 1 minute per user (via `Cache-Control` header)## 6. Mini App API Endpoints- Define nature-inspired colors as CSS custom properties



**Rationale**:- Apply Apple design principles: clean whitespace, readable typography, subtle shadows

- Reduces database queries during typical user session

- Meets <3 second load time target### Decision: RESTful JSON API- Use CSS Grid for responsive layout (single column for mobile, adjustable for tablet)

- Respects data freshness (5-minute window acceptable for approval status)

- No external CSS framework (Bootstrap, Tailwind rejected per KISS)

**Alternatives considered**:

- No caching (query every time): Rejected—would exceed 3-second load target under load**What was chosen**:

- Infinite caching: Rejected—revoked users would see stale data

**Color definitions** (with hex codes):

---

- `GET /api/mini-app/init` - Initialization (registration status + menu config)```css

## 11. Mobile Responsiveness

- `GET /api/mini-app/verify-registration` - Verify current user registration--color-pine: #2D5016;      /* Forest green (primary accent) */

### Decision: CSS Media Queries (Mobile-First Design)

- `POST /api/mini-app/menu-action` - Placeholder for future interactions--color-water: #0099CC;     /* Aqua/teal (secondary accent) */

**What was chosen**:

- Base CSS targets mobile (< 600px width)--color-sand: #D4A574;      /* Beige (neutral accent, warm) */

- Media queries expand layout for tablet+ (> 600px)

- Single-column layout for mobile, optional 2-column for tablet**Rationale**:--color-text: #1a1a1a;      /* Dark gray for text */

- Touch-friendly tap targets (min 44px height, 10px padding)

--color-bg: #f5f5f5;        /* Light background */

**Rationale**:

- Telegram Mini Apps are primarily accessed on mobile- RESTful convention aligns with FastAPI best practices--color-border: #e0e0e0;    /* Subtle borders */

- Meets accessibility standards (WCAG touch target sizes)

- No additional framework needed (CSS only)- JSON responses simple and universal```



**Alternatives considered**:- No GraphQL complexity needed for MVP

- Desktop-first design: Rejected—minority use case for Telegram

- Fixed single-column only: Rejected—wastes space on tablets, violates responsive design**Rationale**:



---**Alternatives considered**:- Nature palette is cohesive and calming



## 12. State Management Between Approval & Mini App Open- CSS variables enable consistent theming



### Decision: Simple Stateless Architecture- GraphQL: Rejected—overkill for 2-3 queries- Meets accessibility standards (WCAG AA contrast ratios)



**What was chosen**:- WebSockets: Rejected—no real-time updates needed- Apple-inspired: sans-serif font, generous padding, minimal decorations

- No complex state machine

- Approval → Send notification message (state: `approved`)- gRPC: Rejected—added complexity

- User opens Mini App → Query database (state fetched on-demand)

- No confirmation required from user to "activate" mini app access**Alternatives considered**:



**Rationale**:---- Custom color scheme per user: Rejected—MVP doesn't require theming complexity

- Minimizes complexity (KISS principle)

- Database is source of truth- Material Design palette: Rejected—contradicts Apple design target specified in feature

- User expectation: open app immediately after approval (no extra steps)

## 7. Error Handling & Fallback UX- Dark mode: Explicitly out of scope for MVP

**Alternatives considered**:

- State machine (pending → approved → activated): Rejected—unnecessary, slows onboarding

- Token-based activation: Rejected—added UX friction, no benefit

### Decision: Graceful Degradation---

---



## Clarifications Resolved

**What was chosen**:## 6. Mini App API Endpoints

All NEEDS CLARIFICATION markers from the specification have been addressed:



1. ✅ **User registration status changes** → Design handles via cache expiration + re-query

2. ✅ **Invalid Telegram ID handling** → Graceful error display, retry logic- Network errors: Display retry button + error message### Decision: RESTful JSON API

3. ✅ **Shared link from approved user** → Mini App enforces per-user verification (each user gets own ID check)

4. ✅ **Registration status verification method** → Database query with Telegram signature validation- Invalid Telegram ID: Display "Unexpected error. Please restart the app."

5. ✅ **Mini App load failure handling** → Error message + retry button

- Registration timeout (>3s): Auto-retry up to 2 times**What was chosen**:

---

- Menu not implemented: Display "Coming soon" placeholder- `GET /api/mini-app/init` - Initialization endpoint (returns user registration status + menu config)

## Next Steps (Phase 1)

- `GET /api/mini-app/verify-registration` - Verify current user's registration (for cache refresh)

Once this research is approved:

1. Generate `data-model.md` with exact schema for unified User model and AccessRequest (renamed from ClientRequest)**Rationale**:- `POST /api/mini-app/menu-action` - Placeholder for future menu interactions (Rule, Pay, Invest)

2. Create API contracts in `contracts/` directory (OpenAPI schema)

3. Develop `quickstart.md` with setup instructions

4. Update agent context with Telegram Web App API and role-based architecture references

- Prevents blank screens**Rationale**:

- Clear user communication- RESTful convention aligns with FastAPI best practices

- No technical jargon (non-technical users)- JSON responses simple and universal

- Handles transient failures- No GraphQL complexity for this MVP

- Contracts can be specified as OpenAPI schema

---

**Alternatives considered**:

## 8. Database Schema Decisions- GraphQL: Rejected—overkill for 2-3 simple queries

- WebSockets: Rejected—no real-time updates needed

### Decision: Extend Existing ClientRequest + New RegisteredUser Table- gRPC: Rejected—added complexity, not needed for web-based Mini App



**What was chosen**:---



- Extend `ClientRequest` with `registered_at` and `is_registered` fields## 7. Error Handling & Fallback UX

- Create new `RegisteredUser` table (quick lookup): telegram_id, is_active, registered_at, mini_app_first_opened_at

- Referential integrity: `RegisteredUser.client_request_id` → `ClientRequest.id`### Decision: Graceful Degradation



**Rationale**:**What was chosen**:

- Network errors: Display retry button + error message (e.g., "Unable to load. Check connection and try again.")

- `ClientRequest` is source of truth for approval workflow- Invalid Telegram ID: Display "Unexpected error. Please restart the app."

- `RegisteredUser` enables fast verification (indexed by telegram_id)- Registration verification timeout (>3 seconds): Auto-retry up to 2 times, then show error

- Audit trail preserved- Menu item not implemented: Display "Coming soon" placeholder message

- Follows existing pattern from 001-request-approval

**Rationale**:

**Alternatives considered**:- Prevents blank screens (bad UX)

- Clear user communication (why something failed)

- Single table: Rejected—less efficient for frequent lookups- No technical jargon (non-technical users)

- Cache in Redis: Rejected—violates YAGNI- Retry logic handles transient failures

- In-memory set: Rejected—lost on restart

**Alternatives considered**:

---- Silent failures with logging: Rejected—poor UX, users confused

- Error codes: Rejected—non-technical users won't understand

## 9. Security Considerations- Automatic reload: Rejected—confusing, risk of infinite loops



### Decision: Verify Telegram User Data Signature---



**What was chosen**:## 8. Database Schema Decisions



- Verify `initData` passed from Telegram WebApp API### Decision: Extend Existing ClientRequest + New RegisteredUser Table

- Validate signature using bot token (HMAC-SHA256)

- Check `auth_date` to prevent replay attacks (±5 min tolerance)**What was chosen**:

- Extract `user.id` and `user.username` only after validation- Extend `ClientRequest` model with `registered_at` and `is_registered` fields

- Create new `RegisteredUser` table (denormalized view for quick lookups) with: telegram_id, is_active, registered_at, mini_app_first_opened_at

**Rationale**:- Maintain referential integrity: `RegisteredUser.client_request_id` → `ClientRequest.id`



- Ensures requests from Telegram**Rationale**:

- Prevents spoofed requests- `ClientRequest` is the source of truth for approval workflow

- Per-request verification (no persistent tokens)- `RegisteredUser` enables fast registration verification (indexed by telegram_id)

- Recommended by Telegram official docs- Audit trail preserved: both tables maintain timestamps

- Follows existing pattern from 001-request-approval

---

**Alternatives considered**:

## 10. Performance & Caching Strategy- Single table with all fields: Rejected—less efficient for frequent lookups, violates normalization

- Cache in Redis: Rejected—violates YAGNI, adds infrastructure

### Decision: Multi-Layer Caching- In-memory set: Rejected—lost on server restart, not suitable for production



**What was chosen**:---



- Browser session storage: Cache registration status for 5 minutes## 9. Security Considerations

- SQLite optimization: Index on `telegram_id`

- FastAPI caching: Cache `/api/mini-app/init` for 1 minute per user### Decision: Verify Telegram User Data Signature



**Rationale**:**What was chosen**:

- On Mini App backend initialization, verify the `initData` passed from Telegram WebApp API

- Reduces database queries- Validate signature using bot token (cryptographic HMAC-SHA256 check)

- Meets <3 second load target- Check `auth_date` to prevent replay attacks (tolerance: ±5 minutes)

- Respects data freshness (5-minute window for approval status)- Extract `user.id` and `user.username` only after validation



---**Rationale**:

- Ensures requests are genuinely from Telegram

## 11. Mobile Responsiveness- Prevents spoofed requests with arbitrary user IDs

- Per-request verification (no persistent tokens)

### Decision: CSS Media Queries (Mobile-First Design)- Recommended by Telegram official docs



**What was chosen**:**Alternatives considered**:

- Trust Telegram context implicitly: Rejected—security risk, not following OAuth best practices

- Base CSS targets mobile (<600px)- JWT token issued by server: Rejected—added complexity, Telegram's built-in mechanism is sufficient

- Media queries expand for tablet+ (>600px)

- Single-column mobile, optional 2-column tablet---

- Touch-friendly tap targets (44px min height)

## 10. Performance & Caching Strategy

**Rationale**:

### Decision: Multi-Layer Caching

- Telegram Mini Apps accessed primarily on mobile

- Meets accessibility (WCAG touch targets)**What was chosen**:

- No additional framework needed- Browser session storage: Cache registration status for 5 minutes

- SQLite query optimization: Index on `client_request.telegram_id` and `registered_user.telegram_id`

---- FastAPI response caching: Cache `/api/mini-app/init` for 1 minute per user (via `Cache-Control` header)



## 12. State Management Between Approval & Mini App**Rationale**:

- Reduces database queries during typical user session

### Decision: Simple Stateless Architecture- Meets <3 second load time target

- Respects data freshness (5-minute window acceptable for approval status)

**What was chosen**:

**Alternatives considered**:

- Approval → Send notification (state: `approved`)- No caching (query every time): Rejected—would exceed 3-second load target under load

- User opens Mini App → Query database- Infinite caching: Rejected—revoked users would see stale data

- No confirmation or "activation" step needed

---

**Rationale**:

## 11. Mobile Responsiveness

- Minimizes complexity (KISS)

- Database is source of truth### Decision: CSS Media Queries (Mobile-First Design)

- User expectation: open immediately after approval

**What was chosen**:

---- Base CSS targets mobile (< 600px width)

- Media queries expand layout for tablet+ (> 600px)

## Clarifications Resolved- Single-column layout for mobile, optional 2-column for tablet

- Touch-friendly tap targets (min 44px height, 10px padding)

All NEEDS CLARIFICATION markers from specification addressed:

**Rationale**:

1. ✅ User registration status changes → Design handles via cache expiration + re-query- Telegram Mini Apps are primarily accessed on mobile

2. ✅ Invalid Telegram ID → Graceful error display, retry logic- Meets accessibility standards (WCAG touch target sizes)

3. ✅ Shared link from approved user → Mini App enforces per-user verification- No additional framework needed (CSS only)

4. ✅ Registration verification method → Database query + Telegram signature validation

5. ✅ Mini App load failure → Error message + retry button**Alternatives considered**:

- Desktop-first design: Rejected—minority use case for Telegram

---- Fixed single-column only: Rejected—wastes space on tablets, violates responsive design



## Next Steps (Phase 1)---



1. Generate `data-model.md` with exact schema## 12. State Management Between Approval & Mini App Open

2. Create API contracts in `contracts/` (OpenAPI)

3. Develop `quickstart.md` with setup instructions### Decision: Simple Stateless Architecture

4. Update agent context

**What was chosen**:
- No complex state machine
- Approval → Send notification message (state: `approved`)
- User opens Mini App → Query database (state fetched on-demand)
- No confirmation required from user to "activate" mini app access

**Rationale**:
- Minimizes complexity (KISS principle)
- Database is source of truth
- User expectation: open app immediately after approval (no extra steps)

**Alternatives considered**:
- State machine (pending → approved → activated): Rejected—unnecessary, slows onboarding
- Token-based activation: Rejected—added UX friction, no benefit

---

## Remaining Clarifications Resolved

All NEEDS CLARIFICATION markers from the specification have been addressed:

1. ✅ **User registration status changes** → Design handles via cache expiration + re-query
2. ✅ **Invalid Telegram ID handling** → Graceful error display, retry logic
3. ✅ **Shared link from approved user** → Mini App enforces per-user verification (each user gets own ID check)
4. ✅ **Registration status verification method** → Database query with Telegram signature validation
5. ✅ **Mini App load failure handling** → Error message + retry button

---

## Next Steps (Phase 1)

Once this research is approved:
1. Generate `data-model.md` with exact schema for `ClientRequest` extensions and `RegisteredUser` table
2. Create API contracts in `contracts/` directory (OpenAPI schema)
3. Develop `quickstart.md` with setup instructions
4. Update agent context with Telegram Web App API reference
