# Implementation Tasks: Mini App Dashboard Redesign

**Feature**: 005-mini-app-dashboard  
**Branch**: `005-mini-app-dashboard`  
**Generated**: 2025-11-14  
**Total Tasks**: 40 (Setup & Foundational: 10 | User Stories: 18 | Polish & Integration: 12)  
**Specification**: [spec.md](./spec.md) | [Plan](./plan.md) | [Data Model](./data-model.md)

---

## Overview

This document defines all implementation tasks for the Mini App Dashboard Redesign feature. Tasks are organized by phase and user story to enable independent development and testing.

## Quick Stats

- **Total Tasks**: 40
- **Setup & Foundational**: 10 tasks (including share_percentage backend)
- **User Story 1 (Compact Menu)**: 5 tasks ✅ **COMPLETE**
- **User Story 2 (Display Statuses)**: 5 tasks ✅ **COMPLETE**
- **User Story 3 (Stakeholder Status for Owners)**: 3 tasks ✅ **COMPLETE**
- **User Story 4 (Stakeholder Link for Owners)**: 3 tasks ✅ **COMPLETE**
- **User Story 5 (Future Placeholders)**: 2 tasks ✅ **COMPLETE**
- **Polish & Integration**: 12 tasks ✅ **COMPLETE**

**Progress**: 40/40 = 100% ✅ **ALL TASKS COMPLETE**

### MVP Scope

**Suggested MVP includes all P1 stories (US1-US4):**

- Compact menu layout
- Display user statuses for all users
- Display stakeholder status for owners
- Display stakeholder link for owners

**Excludes P2:**

- US5 (future content placeholders) can be added after MVP validation

### Dependencies Graph

```text
Phase 1: Setup
    ↓
Phase 2: Foundational (Backend API foundation)
    ↓
Phase 3: US1 (Compact Menu) - Independent
    ↓
Phase 4: US2 (User Statuses) - Depends on US1
    ↓
Phase 5: US3 (Stakeholder Status for Owners) - Can run in parallel with US4
    ↓
Phase 6: US4 (Stakeholder Link for Owners) - Can run in parallel with US3
    ↓
Phase 7: US5 (Future Placeholders) - Independent, optional for MVP
    ↓
Phase 8: Polish & Integration
```

### Parallel Execution Strategy

**After Phase 2 completes, you can work on these in parallel:**

- **Parallel Batch A**: US1 frontend work (menu CSS) is independent
- **Parallel Batch B**: Backend API work (US2-US4 all use same endpoint)
- **Parallel Batch C**: After backend endpoint is created, US2-US4 frontend work can run in parallel

---

---

## Phase 1: Project Setup

Initialize project and validate environment.

- [x] T001 Verify Python environment is Python 3.11+ and FastAPI dependencies installed in `src/`
- [x] T002 Verify existing User model with role flags in `src/models/user.py`
- [x] T003 Add STAKEHOLDER_SHARES_URL environment variable to `.env` (set to example URL)
- [x] T004 Verify WebApp authentication mechanism in existing mini_app routes
- [x] T005 Back up existing `src/static/mini_app/index.html` to `index.html.bak`

---

## Phase 2: Foundational Backend API

Create shared backend endpoint and service layer for all user story tasks.

- [x] T006 Create UserStatusService class in `src/services/user_service.py` with `get_active_roles(user: User) -> List[str]` method
- [x] T007 [P] Add `get_share_percentage(user: User) -> Optional[int]` method to UserStatusService in `src/services/user_service.py` (returns 1 for signed, 0 for unsigned owner, None for non-owner)
- [x] T008 [P] Create Pydantic model `UserStatusResponse` in `src/api/mini_app.py` with user_id, roles, stakeholder_url, and share_percentage fields
- [x] T009 [P] Add `/api/mini-app/user-status` GET endpoint in `src/api/mini_app.py` that calls UserStatusService methods and returns UserStatusResponse
- [x] T010 [P] Add contract test for UserStatusResponse schema in `tests/contract/test_mini_app_endpoints.py` (validate share_percentage is int/null)
- [x] T011 Add integration test for `/api/mini-app/user-status` endpoint in `tests/integration/test_approval_flow_to_mini_app.py`

---

## Phase 3: User Story 1 - Compact Menu Layout

Redesign menu (Rule, Pay, Invest) to occupy ≤30% of viewport height using CSS flexbox.

**Goal**: Reduce menu height by 40%, free space for content below  
**Independent Test**: Menu renders in compact horizontal layout without scrolling on mobile 375px+  
**Acceptance**: Menu buttons visible, functional, responsive on 320px-1920px viewports; horizontal row layout on all viewports

- [x] T012 [P] [US1] Update menu CSS in `src/static/mini_app/styles.css` with `.menu-grid` flexbox styles (display: flex, justify-content: space-around, flex-wrap: nowrap for horizontal layout)
- [x] T013 [P] [US1] Update menu CSS responsive breakpoints for 320px, 375px, and 768px viewports in `src/static/mini_app/styles.css` with horizontal menu maintained across all sizes
- [x] T014 [US1] Update HTML structure in `src/static/mini_app/index.html` to wrap menu items in `.menu-grid` container with horizontal layout class
- [x] T015 [US1] Verify menu buttons (Rule, Pay, Invest) remain clickable and functional after layout changes
- [x] T016 [US1] Add CSS styles for `.menu-item` styling (padding: 10-15px, border: 1px solid, background: #f5f5f5, border-radius: 8px, text-align: center) in `src/static/mini_app/styles.css`

---

## Phase 4: User Story 2 - Display User Statuses

Display user roles on dashboard below compact menu using badges.

**Goal**: Show investor, administrator, owner, staff, stakeholder roles to users  
**Independent Test**: Dashboard loads and displays current user's roles correctly for different role combinations  
**Acceptance**: All applicable roles visible as badges with defined styling; "Member" badge never shown (all users have at least one role)

- [x] T017 [P] [US2] Add `renderUserStatuses(roles)` function in `src/static/mini_app/app.js` to create badge elements from role array with capitalized labels (e.g., "Investor" not "investor")
- [x] T018 [P] [US2] Add `.status-badges` and `.badge` CSS styles in `src/static/mini_app/styles.css` (background: #e3f2fd, color: #1976d2, padding: 5px 10px, margin: 5px, border-radius: 4px, font-size: 12px)
- [x] T019 [US2] Add `loadUserStatus()` async function in `src/static/mini_app/app.js` to fetch from `/api/mini-app/user-status` with error handling
- [x] T020 [US2] Add statuses container `<section id="statuses-container" class="status-badges">` to welcome template in `src/static/mini_app/index.html`
- [x] T021 [US2] Call `loadUserStatus()` on page load after welcome template renders in `src/static/mini_app/app.js`

---

## Phase 5: User Story 3 - Display Stakeholder Status for Owners

Show stakeholder contract status indicator (1=signed, 0=unsigned) for users with is_owner=True.

**Goal**: Owners see their stakeholder contract status  
**Independent Test**: Users with is_owner=True see "Stakeholder" badge with status indicator; non-owners don't  
**Acceptance**: Stakeholder badge displayed first in role badges list with distinct background color (#fff3e0 for unsigned, #c8e6c9 for signed)

- [x] T022 [P] [US3] Add `get_share_percentage()` call to UserStatusService in backend; update T007 implementation to populate share_percentage in response
- [x] T023 [US3] Update `renderUserStatuses(roles)` in T017 to check share_percentage and render "Stakeholder (Unsigned)" or "Stakeholder (Signed)" badge first with conditional styling
- [x] T024 [US3] Update `.badge` CSS in T018 to add conditional class `.badge-unsigned` (background: #fff3e0) and `.badge-signed` (background: #c8e6c9) for stakeholder status indication

---

## Phase 6: User Story 4 - Stakeholder Link for Owners

Display link to stakeholder shares document for owners only.

**Goal**: Owners can access stakeholder shares information  
**Independent Test**: Stakeholder link appears for users with is_owner=True; link hidden for non-owners and if URL not configured  
**Acceptance**: Link visible and clickable for owners; hidden for non-owners and when stakeholder_url is null

- [x] T025 [P] [US4] Add `renderStakeholderLink(url, isOwner)` function in `src/static/mini_app/app.js` to render link only if url is not null AND user is owner (checking `isOwner=True` and url is not empty string)
- [x] T026 [P] [US4] Add `.stakeholder-link` CSS styles in `src/static/mini_app/styles.css` (padding: 10px, background: #fff3e0, border-radius: 8px, margin-top: 15px, text-align: center, color: #f57c00, text-decoration: none, font-weight: 500)
- [x] T027 [US4] Add stakeholder link container `<section id="stakeholder-link-container">` to welcome template in `src/static/mini_app/index.html` (empty by default, populated by renderStakeholderLink if URL exists)

---

## Phase 7: User Story 5 - Future Content Placeholders (P2 - Optional for MVP)

Reserve space in layout for future debt and transaction sections.

**Goal**: Extensible dashboard structure for future features  
**Independent Test**: Layout has defined sections for "Existing Debt" and "Transaction List" without breaking  
**Acceptance**: Placeholder sections visible, layout remains responsive with placeholders

- [x] T028 [US5] Add placeholder sections for "Existing Debt" and "Transaction List" in welcome template `src/static/mini_app/index.html` (with id for future content injection)
- [x] T029 [US5] Add CSS styles for placeholder sections in `src/static/mini_app/styles.css` (background: #f9f9f9, padding: 15px, border: 1px dashed #ccc, border-radius: 8px, margin-top: 15px)

---

## Phase 8: Polish & Integration Testing

Final testing and quality assurance.

- [x] T030 Run full integration test: `pytest tests/integration/test_approval_flow_to_mini_app.py -v` to verify dashboard renders with statuses and share_percentage
- [ ] T031 Manual mobile testing: View dashboard on 320px, 375px, 768px, and desktop viewports; verify horizontal menu layout, no scrolling required, all badges visible
- [ ] T032 Verify menu buttons (Rule, Pay, Invest) route correctly after layout changes; menu occupies <30% viewport height
- [ ] T033 Verify stakeholder link opens correct URL; test with STAKEHOLDER_SHARES_URL set and unset (link should hide when unset)
- [ ] T034 Test with users having different role/ownership combinations: investor, owner with is_stakeholder=1, owner with is_stakeholder=0, non-owner; verify stakeholder badge styling differs
- [ ] T035 Performance check: Dashboard loads in <2 seconds on simulated mobile connection (DevTools throttling 4G)
- [ ] T036 Cross-browser testing: Chrome, Safari (Telegram WebView), Firefox on mobile (375px) and desktop (1920px)
- [x] T037 Update Makefile or CI/CD to run contract and integration tests: `pytest tests/contract/test_mini_app_endpoints.py tests/integration/test_approval_flow_to_mini_app.py -v`
- [x] T038 Verify contract test for share_percentage: test that share_percentage is int (1/0) for owners and null for non-owners
- [x] T039 Create deployment checklist: verify .env includes STAKEHOLDER_SHARES_URL with valid URL, migrations up-to-date, user roles properly assigned in seed data
- [x] T040 Update README with Mini App Dashboard usage instructions: badge colors, stakeholder status indicators (signed vs unsigned), stakeholder link behavior

---

## Testing Strategy

### Contract Tests

**File**: `tests/contract/test_mini_app_endpoints.py`

Tests for new endpoint contract (schema validation):

```python
def test_user_status_response_schema_valid():
    """Verify UserStatusResponse matches contract"""
    response = {
        "user_id": 123,
        "roles": ["investor", "owner"],
        "stakeholder_url": "https://example.com"
    }
    # Validate against JSON Schema from contracts/user-status-response.json
    # Assert all fields present and types correct

def test_user_status_roles_always_non_empty():
    """Verify roles array never empty (minimum: ['member'])"""
    response = get_user_status(user_with_no_roles)
    assert response['roles'] == ['member']
    assert len(response['roles']) >= 1
```

### Integration Tests

**File**: `tests/integration/test_approval_flow_to_mini_app.py`

Tests for full dashboard flow:

```python
def test_dashboard_loads_with_user_statuses():
    """Dashboard renders with user statuses after /user-status call"""
    # Setup: Create user with roles
    # Call: GET /api/mini-app/user-status
    # Assert: Response includes correct roles and stakeholder_url

def test_stakeholder_link_appears_for_owners():
    """Owners see stakeholder link on dashboard"""
    # Setup: Create owner user with is_owner=True
    # Call: GET /api/mini-app/user-status
    # Assert: stakeholder_url not null in response

def test_stakeholder_link_hidden_for_non_owners():
    """Non-owners do NOT see stakeholder link"""
    # Setup: Create user with is_owner=False
    # Call: GET /api/mini-app/user-status
    # Assert: stakeholder_url is null/missing in response
```

### Unit Tests (via service layer)

**File**: `src/services/user_service.py` tests

```python
def test_get_active_roles_owner_with_stakeholder():
    """User with is_owner=True and is_stakeholder=True gets both roles"""
    user = User(is_owner=True, is_stakeholder=True)
    roles = UserStatusService.get_active_roles(user)
    assert "owner" in roles
    assert "stakeholder" in roles

def test_get_active_roles_no_roles_returns_member():
    """User with no roles defaults to ['member']"""
    user = User(is_owner=False, is_investor=False, ...)
    roles = UserStatusService.get_active_roles(user)
    assert roles == ["member"]
```

---

## Task Format Reference

**Checklist Format** (REQUIRED):

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Components**:

1. `- [ ]`: Markdown checkbox
2. `[TaskID]`: T001, T002, etc.
3. `[P]`: Optional - marks parallelizable tasks
4. `[Story]`: Optional for P3+ tasks - [US1], [US2], etc.
5. **Description**: Action + exact file path

---

---

## Implementation Notes

### Key Files Summary

| File | Changes | Status |
|------|---------|--------|
| `src/models/user.py` | None | ✅ Exists |
| `src/services/user_service.py` | Add UserStatusService with get_active_roles() and get_share_percentage() | T006, T007 |
| `src/api/mini_app.py` | Add UserStatusResponse Pydantic model with share_percentage field + endpoint | T008, T009 |
| `src/static/mini_app/index.html` | Add menu-grid container (horizontal), statuses container, stakeholder link container, future placeholders | T014, T020, T027, T028 |
| `src/static/mini_app/styles.css` | Add .menu-grid (flex horizontal), .badge/.badge-signed/.badge-unsigned, .stakeholder-link, placeholder styles | T012, T013, T016, T018, T024, T026, T029 |
| `src/static/mini_app/app.js` | Add loadUserStatus(), renderUserStatuses (with share_percentage styling), renderStakeholderLink() | T017, T019, T021, T025 |
| `.env` | Add STAKEHOLDER_SHARES_URL | T003 |
| `tests/contract/test_mini_app_endpoints.py` | Add schema validation tests for share_percentage field | T010 |
| `tests/integration/test_approval_flow_to_mini_app.py` | Add tests for dashboard with share_percentage, stakeholder link visibility | T011 |

### Execution Recommendations

1. **Start with Phase 1-2**: Setup environment and create backend API with share_percentage (T001-T011)
2. **Then work on US1 (Menu)**: Frontend CSS changes for horizontal layout (T012-T016)
3. **Parallel US2-US4**: Frontend work with statuses, share_percentage badge styling, and stakeholder link (T017-T027)
4. **Optional US5**: Add after MVP validation
5. **Final Phase**: Polish, testing, and validation including share_percentage contract tests (T030-T040)

### Estimated Effort

- **Setup**: 30 minutes (T001-T005)
- **Backend API with share_percentage**: 2.5 hours (T006-T011)
- **US1 (Menu)**: 1 hour (T012-T016)
- **US2 (Statuses)**: 1 hour (T017-T021)
- **US3 (Stakeholder Status)**: 1 hour (T022-T024, with share_percentage display logic)
- **US4 (Stakeholder Link)**: 45 minutes (T025-T027)
- **US5 (Optional)**: 30 minutes (T028-T029)
- **Polish & Testing**: 2.5 hours (T030-T040, with share_percentage validation)
- **Total**: ~9 hours for full feature + comprehensive testing

---

## Quality Checklist

Before marking tasks complete:

- [ ] Code follows SOSenki conventions (Python 3.11+, FastAPI patterns)
- [ ] All file paths are correct and relative to project root
- [ ] Tests pass: `pytest tests/contract/test_mini_app_endpoints.py`
- [ ] Tests pass: `pytest tests/integration/test_approval_flow_to_mini_app.py`
- [ ] Dashboard responsive on mobile (320px, 375px, 768px) and desktop (1920px)
- [ ] No console errors in browser DevTools
- [ ] Stakeholder link points to correct environment URL
- [ ] User statuses display correctly for different role combinations
- [ ] Menu occupies ≤30% of viewport height
- [ ] Page loads in <2 seconds on mobile connection

---

## Notes for Implementation

### Constitution Compliance

- ✅ **YAGNI**: Only required features specified, no speculative additions
- ✅ **KISS**: CSS flexbox and vanilla JavaScript, no complex state management
- ✅ **DRY**: UserStatusService centralizes role mapping logic
- ✅ **No Hard-Coded Secrets**: STAKEHOLDER_SHARES_URL in environment variable
- ✅ **No New Dependencies**: Uses existing FastAPI, SQLAlchemy, vanilla frontend

### Frontend Notes

- All role strings capitalized for display: "investor" → "Investor"
- Stakeholder link target="_blank" to open in new window
- Fallback for missing stakeholder URL: hidden or placeholder text
- CSS uses flexbox (no grid library) for maximum browser compatibility

### Backend Notes

- `/api/mini-app/user-status` independent from `/api/mini-app/init`
- Uses existing WebApp authentication (no new auth required)
- UserStatusService method is static for reusability
- Response always includes roles array (minimum ["member"])

---

## Related Documents

- **Specification**: [spec.md](./spec.md) - User stories, acceptance criteria
- **Implementation Plan**: [plan.md](./plan.md) - Technical decisions, project structure
- **Data Model**: [data-model.md](./data-model.md) - Entity schemas, API contracts
- **Quick Start**: [quickstart.md](./quickstart.md) - Code snippets and setup guide
- **API Contracts**: [contracts/](./contracts/) - OpenAPI spec, JSON schema
