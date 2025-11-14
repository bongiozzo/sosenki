# Feature Specification: Mini App Dashboard Redesign

**Feature Branch**: `005-mini-app-dashboard`  
**Created**: 2025-11-14  
**Status**: Draft  
**Input**: Transform menu layout, display user statuses and stakeholder information on first page

## User Scenarios & Testing

### User Story 1 - Compact Menu Layout (Priority: P1)

Registered users need a more compact menu layout on the first page that uses space efficiently and allows for future menu items to be added without crowding the interface.

**Why this priority**: This is the foundation for the dashboard redesign. All other content depends on freeing up space by making the menu more compact. Without this, there's no room for personal statuses, debt, and transactions.

**Independent Test**: The menu (Rule, Pay, Invest) can be rendered in a horizontal layout that takes up less than 30% of the visible viewport height, leaving ample space for content below. Can be fully tested independently and deployed without content sections.

**Acceptance Scenarios**:

1. **Given** a registered user opens the Mini App, **When** the welcome page loads, **Then** the menu displays Rule, Pay, and Invest buttons in a compact horizontal row layout
2. **Given** the menu is in compact layout, **When** the user views the page on mobile (small screen), **Then** the menu remains visible and functional without excessive scrolling
3. **Given** the compact menu layout, **When** future menu items are added, **Then** the layout gracefully accommodates new items without collapsing or becoming unusable

---

### User Story 2 - Display User Statuses (Priority: P1)

Registered users need to see their personal roles and status (investor, administrator, owner, staff, stakeholder) displayed on the main dashboard to understand their access level and capabilities within the system.

**Why this priority**: Knowing one's role is fundamental to understanding what features are available. This builds user confidence and reduces support requests about access levels.

**Independent Test**: The statuses section displays the current user's active roles (from is_investor, is_administrator, is_owner, is_staff, is_stakeholder flags). Can be tested by loading the dashboard for users with different role combinations and verifying the correct statuses appear.

**Acceptance Scenarios**:

1. **Given** a registered user with multiple roles (e.g., owner and investor), **When** the dashboard loads, **Then** all applicable roles are displayed visibly in the content area below the menu
2. **Given** a registered user with no additional roles (only is_active=True), **When** the dashboard loads, **Then** the statuses section displays all users with at least a "Member" role indicator badge (no empty state)
3. **Given** a user with is_stakeholder=True, **When** the dashboard loads, **Then** stakeholder status is prominently included in the displayed statuses (rendered as first badge in the list, with distinct background color)

---

### User Story 3 - Display Stakeholder Status for Owners (Priority: P1)

Property owners need to see their stakeholder status (contract status indicator: 1 for signed, 0 for unsigned) displayed on the dashboard, with a link to view the full stakeholder shares document.

**Why this priority**: Owners need quick access to their stakeholder contract status. This indicates whether their ownership contract is finalized.

**Independent Test**: The dashboard shows stakeholder status indicator for users with is_owner=True. The stakeholder shares link is present and points to the correct URL from environment configuration.

**Acceptance Scenarios**:

1. **Given** a user with is_owner=True, **When** the dashboard loads, **Then** a "Stakeholder" badge is displayed in the statuses section with an indicator (1=signed, 0=unsigned) conveyed by distinct styling
2. **Given** a user with is_owner=True, **When** the dashboard loads, **Then** a link labeled "Stakeholder Shares" (or similar) is visible and points to the stakeholder shares URL from environment
3. **Given** a user with is_owner=True, **When** they click the stakeholder shares link, **Then** it opens the URL defined in the application environment (STAKEHOLDER_SHARES_URL)

---

### User Story 4 - Stakeholder Shares Link for Owners (Priority: P1)

Property owners need access to a link to view the stakeholder shares document containing the legally accepted list of stakeholders and ownership structure information.

**Why this priority**: Owners need to access the authoritative stakeholder information for legal and administrative purposes. This information is not relevant for non-owners.

**Independent Test**: The stakeholder shares link appears on the dashboard for users with is_owner=True, pointing to the stakeholder shares URL from environment configuration. Link is hidden for non-owners.

**Acceptance Scenarios**:

1. **Given** a user with is_owner=True, **When** the dashboard loads, **Then** a link to "Stakeholder Shares" is displayed
2. **Given** a user with is_owner=True, **When** they click the stakeholder shares link, **Then** it opens the stakeholder shares URL defined in the STAKEHOLDER_SHARES_URL environment variable
3. **Given** a user with is_owner=False, **When** the dashboard loads, **Then** no stakeholder shares link is displayed

---

### User Story 5 - Future Content Placeholders (Priority: P2)

The dashboard reserves space and provides structure for future content additions (existing debt, transaction lists) without implementing these features in this release.

**Why this priority**: P2 because future content isn't implemented yet, but the structure should accommodate it. This ensures the dashboard design is extensible.

**Independent Test**: The dashboard layout has clear sections or placeholders where debt information and transaction lists will be added in future releases. The layout doesn't break when these sections are added later.

**Acceptance Scenarios**:

1. **Given** the dashboard redesign is complete, **When** the page structure is reviewed, **Then** space or sections are reserved for "Existing Debt" and "Transaction List" content
2. **Given** future implementations add debt and transaction sections, **When** they are integrated, **Then** the compact menu and statuses remain intact and properly positioned

---

### Edge Cases

- What happens if a user has no roles assigned (only is_active=True)? → All users display at least "Member" role badge (no empty state); edge case should not occur in normal operation
- What if the stakeholder shares URL is not configured in environment? → API returns null/empty string for stakeholder_url; frontend does NOT render the stakeholder link section (graceful fallback)
- What if a user's role configuration changes while they're viewing the dashboard? → Statuses are displayed based on current data; user may need to refresh to see updates (not real-time in MVP)
- What if the screen is very small (mobile)? → Menu and content should remain readable with appropriate responsive design

## Requirements

### Functional Requirements

- **FR-001**: System MUST display a compact menu containing Rule, Pay, and Invest buttons that uses no more than 30% of the viewport height on desktop (no more than 2 rows of content)
- **FR-002**: System MUST display user roles/statuses in a dedicated content area below the compact menu, showing values of: is_investor, is_administrator, is_owner, is_staff, is_stakeholder
- **FR-003**: System MUST display a "Stakeholder Shares" link that points to a URL configured in environment (to be added as STAKEHOLDER_SHARES_URL in .env)
- **FR-004**: The stakeholder shares link MUST be visible for users with is_owner=True (owners)
- **FR-005**: The stakeholder shares link MUST be hidden for users with is_owner=False (non-owners)
- **FR-006**: System MUST maintain existing menu functionality (Rule, Pay, Invest buttons remain clickable and route correctly)
- **FR-007**: System MUST reserve space/sections in the layout for future content: "Existing Debt" and "Transaction List" (not implemented, structure only)
- **FR-008**: System MUST render the dashboard responsively for mobile, tablet, and desktop viewports

### Key Entities

- **User**: Represented by roles (is_investor, is_administrator, is_owner, is_staff, is_stakeholder flags) and stakeholder status
- **Stakeholder Shares**: External document/URL containing ownership share information for the property/cooperative
- **Dashboard Content Sections**:
  - Menu Section (compact layout)
  - User Statuses Section (new)
  - Stakeholder Status/Shares Link (new)
  - Debt Section (future placeholder)
  - Transactions Section (future placeholder)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Dashboard loads in under 2 seconds for users on typical mobile connections
- **SC-002**: User statuses and stakeholder share link are visible and accessible on first page load without scrolling (on mobile screens 375px wide or larger)
- **SC-003**: 95% of users with roles assigned can immediately identify their roles on the dashboard
- **SC-004**: Stakeholder shares link has 100% click-through success rate (no broken links or errors)
- **SC-005**: Responsive design maintains usability on screens from 320px (small mobile) to 1920px (desktop) width
- **SC-006**: Layout accommodation for future debt and transaction sections doesn't require dashboard redesign (extensible structure proven)
- **SC-007**: Menu compaction reduces welcome page height by at least 40% compared to previous design, freeing space for content

## Assumptions

1. **STAKEHOLDER_SHARES_URL Environment Variable**: The application will have a new environment variable (STAKEHOLDER_SHARES_URL) configured in .env pointing to the stakeholder shares document
2. **Statuses Display**: User roles will be displayed as human-readable labels (e.g., "Investor", "Administrator", "Owner") rather than code values
3. **Mobile-First Approach**: Dashboard design prioritizes mobile experience first, then scales to larger screens
4. **No Real-Time Updates**: Role changes are reflected on next page load; this is not a real-time reactive system
5. **Stakeholder Information**: Stakeholder shares is a read-only external resource; users cannot modify it from the dashboard
6. **Future Content Structure**: Space reserved for debt/transactions can be simple CSS layout adjustments; no database schema changes needed

## Dependencies

- **Frontend**: HTML (index.html), CSS (styles.css), JavaScript (app.js) in `src/static/mini-app/`
- **Backend API**: Existing `/api/mini-app/init` endpoint or new endpoint to provide user status information
- **Database**: User model (user.py) with role flags already exists; no schema changes needed
- **Environment Configuration**: New STAKEHOLDER_SHARES_URL environment variable must be added to .env
