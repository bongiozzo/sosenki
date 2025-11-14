# Quick Start: Mini App Dashboard Redesign

**Feature**: [specs/005-mini-app-dashboard/](./spec.md)  
**Branch**: `005-mini-app-dashboard`

## What's Being Built

Redesigned SOSenki mini-app welcome screen with:
- Compact **horizontal** menu (Rule, Pay, Invest) using CSS Flexbox
- User statuses display as badges (investor, administrator, owner, staff, stakeholder)
- Stakeholder contract status indicator (1=signed, 0=unsigned) for owners
- Stakeholder shares link for all users (hidden if URL not configured)
- Responsive layout for mobile (320px) to desktop (1920px)

## Files to Modify

### Backend

**1. Add new endpoint in `src/api/mini_app.py`**

```python
@router.get("/user-status")
async def get_user_status(request: Request):
    """Get user's roles and stakeholder information."""
    user_id = request.state.user_id  # From existing auth mechanism
    user = await user_service.get_user(user_id)
    roles = UserStatusService.get_active_roles(user)
    share_percentage = UserStatusService.get_share_percentage(user)
    stakeholder_url = os.getenv("STAKEHOLDER_SHARES_URL") or None
    return {
        "user_id": user_id,
        "roles": roles,
        "share_percentage": share_percentage,
        "stakeholder_url": stakeholder_url
    }
```

**2. Add methods to `src/services/user_service.py`**

```python
class UserStatusService:
    @staticmethod
    def get_active_roles(user: User) -> List[str]:
        """Extract human-readable active roles from User model."""
        roles = []
        if user.is_investor:
            roles.append("investor")
        if user.is_administrator:
            roles.append("administrator")
        if user.is_owner:
            roles.append("owner")
        if user.is_staff:
            roles.append("staff")
        if user.is_stakeholder:
            roles.append("stakeholder")
        return sorted(roles) or ["member"]
    
    @staticmethod
    def get_share_percentage(user: User) -> Optional[int]:
        """Return stakeholder contract status (1=signed, 0=unsigned, None if non-owner)."""
        if not user.is_owner:
            return None
        return 1 if user.is_stakeholder else 0
```

**3. Update environment configuration**

Add to `.env`:
```
STAKEHOLDER_SHARES_URL=https://docs.example.com/stakeholder-shares
```

### Frontend

**1. Update `src/static/mini_app/styles.css`**

Add compact menu styles (horizontal row layout):

```css
.menu-grid {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  flex-wrap: nowrap;
  gap: 10px;
  margin-bottom: 20px;
}

.menu-item {
  flex: 1 1 auto;
  max-width: 150px;
  padding: 15px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background: #f5f5f5;
  cursor: pointer;
  font-size: 14px;
  text-align: center;
}

.status-badges {
  margin-top: 20px;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 8px;
}

.badge {
  display: inline-block;
  padding: 5px 10px;
  margin: 5px;
  background: #e3f2fd;
  border-radius: 4px;
  font-size: 12px;
  color: #1976d2;
  font-weight: 500;
}

.badge-signed {
  background: #c8e6c9;
  color: #2e7d32;
}

.badge-unsigned {
  background: #fff3e0;
  color: #f57c00;
}

.stakeholder-link {
  display: block;
  margin-top: 15px;
  padding: 10px;
  background: #fff3e0;
  border-radius: 8px;
  text-decoration: none;
  color: #f57c00;
  text-align: center;
  font-weight: 500;
}

.placeholder-section {
  background: #f9f9f9;
  border: 1px dashed #ccc;
  border-radius: 8px;
  padding: 15px;
  margin-top: 15px;
  color: #999;
}
```
  border-radius: 4px;
  font-size: 12px;
  color: #1976d2;
}

.stakeholder-link {
  display: block;
  margin-top: 15px;
  padding: 10px;
  background: #fff3e0;
  border-radius: 8px;
  text-decoration: none;
  color: #f57c00;
  text-align: center;
  font-weight: 500;
}

@media (min-width: 375px) {
  .menu-item {
    font-size: 16px;
    padding: 15px;
  }
}

@media (min-width: 768px) {
  .menu-grid {
    max-height: 100px;
  }
}
```

**2. Update `src/static/mini_app/app.js`**

Add functions to load and display statuses with share percentage indicator:

```javascript
async function loadUserStatus() {
  try {
    const response = await fetch('/api/mini-app/user-status');
    if (!response.ok) throw new Error('Failed to load status');
    
    const data = await response.json();
    renderUserStatuses(data.roles, data.share_percentage);
    if (data.stakeholder_url) {
      renderStakeholderLink(data.stakeholder_url);
    }
  } catch (error) {
    console.error('Error loading user status:', error);
  }
}

function renderUserStatuses(roles, sharePercentage) {
  const container = document.querySelector('#statuses-container');
  
  // Sort roles with "stakeholder" first if present
  const sortedRoles = roles.filter(r => r !== 'stakeholder')
    .concat(roles.includes('stakeholder') ? ['stakeholder'] : []);
  
  container.innerHTML = sortedRoles.map(role => {
    let badgeHtml = `<span class="badge`;
    
    // Add special styling for stakeholder status
    if (role === 'stakeholder' && sharePercentage !== null) {
      badgeHtml += sharePercentage === 1 ? ' badge-signed' : ' badge-unsigned';
      const status = sharePercentage === 1 ? 'Signed' : 'Unsigned';
      badgeHtml += `">Stakeholder (${status})</span>`;
    } else {
      const displayName = role.charAt(0).toUpperCase() + role.slice(1);
      badgeHtml += `">${displayName}</span>`;
    }
    
    return badgeHtml;
  }).join('');
}

function renderStakeholderLink(url) {
  const container = document.querySelector('#stakeholder-link-container');
  if (!url) {
    container.innerHTML = '';  // Hide link if URL not provided
    return;
  }
  
  container.innerHTML = `
    <a href="${url}" class="stakeholder-link" target="_blank" rel="noopener noreferrer">
      View Stakeholder Shares
    </a>
  `;
}

// Call after welcome template renders
loadUserStatus();
```

**3. Update `src/static/mini_app/index.html`**

In the welcome template, add containers below menu:

```html
<template id="welcome-template">
  <div class="welcome-container">
    <header class="header">
      <h1 class="brand">SOSenki</h1>
      <p class="tagline">Welcome back, <span id="user-name">User</span></p>
    </header>
    
    <main class="main-menu">
      <nav class="menu-grid">
        <!-- Existing menu items (Rule, Pay, Invest) -->
      </nav>
    </main>
    
    <!-- New: User statuses section -->
    <section id="statuses-container" class="status-badges"></section>
    
    <!-- New: Stakeholder link section -->
    <section id="stakeholder-link-container"></section>
  </div>
</template>
```

## Testing

### Backend Tests

Add to `tests/contract/test_mini_app_endpoints.py`:

```python
def test_user_status_endpoint_with_roles(client, test_user_with_roles):
    """Test user-status endpoint returns roles and stakeholder URL."""
    response = client.get('/api/mini-app/user-status', 
                         headers={'Authorization': f'Bearer {test_user_with_roles.token}'})
    assert response.status_code == 200
    data = response.json()
    assert 'user_id' in data
    assert 'roles' in data
    assert 'stakeholder_url' in data
    assert isinstance(data['roles'], list)
    assert len(data['roles']) > 0
```

### Frontend Tests

Add to `tests/integration/test_approval_flow_to_mini_app.py`:

```python
def test_dashboard_displays_user_statuses(selenium_client):
    """Test dashboard renders user statuses after load."""
    selenium_client.get('/mini-app/')
    # Wait for API call to complete
    selenium_client.wait_for_element('.status-badges')
    badges = selenium_client.find_elements('.badge')
    assert len(badges) > 0
```

## Deployment Steps

1. **Create feature branch**: Already on `005-mini-app-dashboard`
2. **Backend**: Add endpoint, service method, update .env
3. **Frontend**: Update HTML, CSS, JavaScript
4. **Test**: Run `make test` to verify contract and integration tests
5. **Code Review**: Verify against Constitution (YAGNI, KISS, DRY)
6. **Merge**: Create PR and merge to main after approval

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Stakeholder shares document URL (for all users to view)
STAKEHOLDER_SHARES_URL=https://docs.example.com/stakeholder-shares
```

For local development, use a public document URL or placeholder.

## Performance Notes

- Dashboard loads in <2 seconds on typical mobile connections (4G)
- API endpoint response size: ~200 bytes (minimal payload)
- No database joins required (uses existing indexed columns)
- Frontend renders synchronously after API response (simple DOM updates)

## Browser Support

- Chrome/Chromium 90+ (native CSS Flexbox)
- Safari 14+ (native CSS media queries)
- Works on Telegram WebApp (uses Chromium 90+ engine)
- Responsive from 320px to 1920px width

---

## References

- **Spec**: [specs/005-mini-app-dashboard/spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/openapi.yaml](./contracts/openapi.yaml)
- **Research**: [research.md](./research.md)
