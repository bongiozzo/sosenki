# Implementation Plan: Mini App Dashboard Redesign

**Branch**: `005-mini-app-dashboard` | **Date**: 2025-11-14 | **Spec**: [specs/005-mini-app-dashboard/spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-mini-app-dashboard/spec.md`

## Summary

Redesign the SOSenki mini-app welcome screen to display a compact menu (Rule, Pay, Invest) that occupies ≤30% of viewport height, freeing space for user statuses display (investor, administrator, owner, staff, stakeholder roles) and a stakeholder shares link. This enables transparency and improves user understanding of their access level while reserving space for future debt and transaction content.

**Technical Approach**: Frontend-only redesign of existing HTML/CSS/JavaScript with new backend API endpoint to provide user status information. No database schema changes required.

## Technical Context

**Language/Version**: Python 3.11+ (backend), HTML5/CSS3/JavaScript (frontend)  
**Primary Dependencies**: FastAPI (existing), python-telegram-bot (existing), WebApp API (Telegram platform)  
**Storage**: SQLite (existing User model, no schema changes)  
**Testing**: pytest for backend endpoint tests, contract tests for API, integration tests for dashboard rendering  
**Target Platform**: Telegram Mini App (browser-based WebApp on mobile Telegram client)  
**Project Type**: Single project (monolithic backend + mini-app frontend)  
**Performance Goals**: Dashboard loads in <2 seconds on typical mobile connections (≤4G)  
**Constraints**: No scrolling required on first load (375px+ mobile screens); responsive from 320px-1920px width  
**Scale/Scope**: Single-page dashboard redesign affecting ~150 lines of HTML/CSS and new backend endpoint

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Evaluation

✅ **YAGNI (You Aren't Gonna Need It)**:

- Spec defines only required features: compact menu, user statuses, stakeholder link
- Future debt/transactions reserved as layout space only (no code/tables/fields added)
- No speculative database columns or migrations planned
- **PASS**: Feature scope is tightly bounded to specification

✅ **KISS (Keep It Simple, Stupid)**:

- Solution uses existing technologies: HTML layout restructuring, CSS flexbox for compact menu
- Backend adds single API endpoint to aggregate existing User model flags
- No complex state management or real-time synchronization
- **PASS**: Straightforward CSS/layout redesign

✅ **DRY (Don't Repeat Yourself)**:

- Reuses existing User model (no duplication of role flags)
- Statuses logic extracted into backend service method (single source of truth)
- **PASS**: No duplication of role/permission logic

✅ **No Hard-Coded Secrets or Paths**:

- Stakeholder URL loaded from environment variable (STAKEHOLDER_SHARES_URL)
- Frontend paths use relative URLs (no hard-coded filesystem paths)
- **PASS**: All configuration externalized

✅ **Dependency Management**:

- No new Python dependencies required (uses existing FastAPI, SQLAlchemy)
- Frontend uses native HTML5/CSS3/JavaScript (no new npm packages)
- **PASS**: No unnecessary dependencies

**GATE STATUS**: ✅ ALL GATES PASS - Ready to proceed to Phase 0 research## Project Structure

### Documentation (this feature)

```text
specs/005-mini-app-dashboard/
├── spec.md              # Feature specification ✓
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (research findings)
├── data-model.md        # Phase 1 output (no schema changes, documentation only)
├── quickstart.md        # Phase 1 output (setup guide)
├── contracts/           # Phase 1 output (API contract definitions)
│   ├── mini-app-init-response.json    # Updated response schema
│   └── openapi.yaml                   # Updated OpenAPI spec
├── checklists/
│   └── requirements.md   # Quality checklist ✓
└── tasks.md             # Phase 2 output (to be created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── api/
│   └── mini_app.py           # UPDATE: Add new user-statuses endpoint
├── services/
│   ├── user_service.py       # ADD: Method to get user statuses
│   └── mini_app_service.py   # NEW (or add to existing): Dashboard data aggregation
├── models/
│   └── user.py               # NO CHANGES: Existing User model with role flags
└── static/
    └── mini_app/
        ├── index.html        # UPDATE: Dashboard layout redesign
        ├── styles.css        # UPDATE: Compact menu CSS, statuses styling
        ├── app.js            # UPDATE: Load and display user statuses
        └── index.html.bak    # (optional) Backup of original layout

tests/
├── contract/
│   └── test_mini_app_endpoints.py    # UPDATE: Add tests for new user-statuses endpoint
├── integration/
│   └── test_approval_flow_to_mini_app.py  # UPDATE: Integration tests for dashboard rendering
└── unit/
    └── (no new unit tests required for this feature)
```

**Structure Decision**: Monolithic single-project structure (existing) is maintained. Feature uses existing `src/api/`, `src/services/`, and `src/static/mini_app/` directories. No new top-level projects or major restructuring required. Changes are additive within existing modules: new endpoint in `api/mini_app.py`, new service method in `services/`, and updates to frontend files.
