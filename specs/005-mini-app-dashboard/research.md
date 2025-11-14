# Research: Mini App Dashboard Redesign

**Phase**: Phase 0 - Outline & Research
**Date**: 2025-11-14
**Feature**: [specs/005-mini-app-dashboard/](./spec.md)

## Overview

All technical decisions documented. No unresolved unknowns. Ready for Phase 1.

## Key Decisions

### Decision 1: CSS Flexbox for Responsive Menu

Uses native CSS, supported in all WebApp browsers. No JavaScript calculations needed.

- Menu container: `display: flex; flex-wrap: wrap`
- Breakpoints: 320px, 375px, 768px
- Target: ≤30% viewport height

### Decision 2: New Backend Endpoint

Create `/api/mini-app/user-status` separate from init endpoint.

- Keeps init lightweight (separation of concerns)
- Returns user roles and stakeholder URL
- New service: `UserStatusService.get_active_roles(user)`

### Decision 3: Environment Variable Configuration

Add `STAKEHOLDER_SHARES_URL` to .env for stakeholder document link.

- Follows Constitution: no hard-coded URLs
- Included in API response
- Dynamic configuration without frontend rebuild

### Decision 4: Vanilla JavaScript Implementation

No framework needed for simple read-only display.

- Single fetch on page load
- DOM updates from response data
- Follows KISS principle

### Decision 5: Mobile Viewport Coverage

- 320-374px: Single column layout
- 375-768px: 3-column grid menu
- 769px+: Desktop layout

### Decision 6: User Roles Service

Method `UserStatusService.get_active_roles(user: User)` maps User model flags to role strings.

- Maps: is_investor, is_administrator, is_owner, is_staff, is_stakeholder
- Default: returns ["member"] if no roles
- Single source of truth

### Decision 7: Backward Compatibility

No changes to `/api/mini-app/init`. New endpoint is independent.

## Phase 0 Complete

✅ All decisions documented
✅ Constitution compliant
✅ No new dependencies
✅ Ready for Phase 1
