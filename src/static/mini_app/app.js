// SOSenki Mini App Client Logic

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand WebApp to full height
tg.expand();

// Ready the WebApp
tg.ready();

// Get app container
const appContainer = document.getElementById('app');

/**
 * Render welcome screen for registered user
 */
function renderWelcomeScreen(data) {
    const template = document.getElementById('welcome-template');
    const content = template.content.cloneNode(true);
    
    // Set user name
    const userNameSpan = content.getElementById('user-name');
    userNameSpan.textContent = data.userName || data.firstName || 'User';
    
    // Handle Invest menu item based on isInvestor flag
    const investItem = content.getElementById('invest-item');
    if (!data.isInvestor) {
        investItem.classList.add('disabled');
        investItem.disabled = true;
    }
    
    // Add click handlers to menu items
    const menuItems = content.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', () => {
            if (!item.classList.contains('disabled')) {
                handleMenuAction(item.dataset.action);
            }
        });
    });
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
}

/**
 * Render access denied screen for non-registered user
 */
function renderAccessDenied(data) {
    const template = document.getElementById('access-denied-template');
    const content = template.content.cloneNode(true);
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
}

/**
 * Render error screen
 */
function renderError(message) {
    const template = document.getElementById('error-template');
    const content = template.content.cloneNode(true);
    
    // Set error message
    const errorMessageEl = content.getElementById('error-message');
    errorMessageEl.textContent = message || 'Please try again later.';
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
}

/**
 * Render user status badges from roles array
 * @param {Array<string>} roles - Array of role strings (e.g., ["investor", "owner"])
 * @param {number|null} sharePercentage - Share percentage (1 for signed owner, 0 for unsigned owner, null for non-owner)
 */
function renderUserStatuses(roles, sharePercentage = null) {
    const container = document.getElementById('statuses-container');
    if (!container) {
        console.warn('Status container not found');
        return;
    }
    
    // Clear existing badges
    container.innerHTML = '';
    
    // Skip rendering if no roles (should not happen - always minimum ["member"])
    if (!roles || roles.length === 0) {
        return;
    }
    
    // Render Stakeholder badge first if user is owner (share_percentage is 1 or 0, not null)
    if (sharePercentage !== null) {
        const stakeholderBadge = document.createElement('span');
        stakeholderBadge.className = 'badge';
        
        if (sharePercentage === 1) {
            // Signed owner
            stakeholderBadge.classList.add('badge-signed');
            stakeholderBadge.textContent = 'Stakeholder (Signed)';
        } else if (sharePercentage === 0) {
            // Unsigned owner
            stakeholderBadge.classList.add('badge-unsigned');
            stakeholderBadge.textContent = 'Stakeholder (Unsigned)';
        }
        
        container.appendChild(stakeholderBadge);
    }
    
    // Filter out "member" role - never show it as badge (all users have at least one role)
    const displayRoles = roles.filter(role => role.toLowerCase() !== 'member');
    
    // Create badge elements for each role
    displayRoles.forEach(role => {
        const badge = document.createElement('span');
        badge.className = 'badge';
        // Capitalize first letter of each word
        badge.textContent = role.charAt(0).toUpperCase() + role.slice(1).toLowerCase();
        container.appendChild(badge);
    });
}

/**
 * Load user status from backend and render badges
 */
async function loadUserStatus() {
    try {
        const initData = tg.initData;
        
        if (!initData) {
            console.error('No Telegram init data available');
            return;
        }
        
        // Fetch user status from backend
        const response = await fetch('/api/mini-app/user-status', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': initData,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error('Failed to load user status:', response.status, response.statusText);
            return;
        }
        
        const data = await response.json();
        
        // Render user roles as badges
        if (data.roles && Array.isArray(data.roles)) {
            renderUserStatuses(data.roles, data.share_percentage);
        }
        
        // Render stakeholder link for owners only
        const isOwner = data.share_percentage !== null; // Owner if share_percentage is 1 or 0 (not null)
        renderStakeholderLink(data.stakeholder_url || null, isOwner);
        
    } catch (error) {
        console.error('Error loading user status:', error);
    }
}

/**
 * Render stakeholder link for owners only
 * @param {string|null} url - Stakeholder shares URL from backend (null if not owner or not configured)
 * @param {boolean} isOwner - Whether the user is an owner
 */
function renderStakeholderLink(url, isOwner = false) {
    const container = document.getElementById('stakeholder-link-container');
    if (!container) {
        console.warn('Stakeholder link container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Only render if user is owner AND url is provided and not empty
    if (!isOwner || !url || url.trim() === '') {
        return;
    }
    
    // Create link element
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'stakeholder-link';
    link.textContent = 'View Stakeholder Shares';
    
    container.appendChild(link);
}

/**
 * Handle menu item click
 */
async function handleMenuAction(action) {
    if (action === 'enjoy') {
        try {
            // Fetch photo gallery URL from backend config
            const response = await fetch('/api/mini-app/config');
            const data = await response.json();
            
            if (data.photoGalleryUrl) {
                // Open external browser with photo gallery URL
                tg.openLink(data.photoGalleryUrl);
            } else {
                tg.showAlert('Photo gallery URL not configured');
            }
        } catch (error) {
            console.error('Error fetching config:', error);
            tg.showAlert('Error opening photo gallery');
        }
        return;
    }
    
    // Show Telegram alert for other features (placeholder)
    tg.showAlert(`Feature "${action}" coming soon!`);
    
    // In future: POST to /api/mini-app/menu-action
}

/**
 * Initialize Mini App
 */
async function initMiniApp() {
    try {
        // Get init data from Telegram WebApp
        const initData = tg.initData;
        
        if (!initData) {
            renderError('Could not verify Telegram authentication. Please open this app from Telegram.');
            return;
        }
        
        // Call backend API to check registration status
        const response = await fetch('/api/mini-app/init', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': initData,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                renderError('Authentication failed. Please restart the app.');
            } else {
                renderError('Server error. Please try again later.');
            }
            return;
        }
        
        const data = await response.json();
        
        // Render appropriate screen based on registration status
        if (data.isRegistered) {
            renderWelcomeScreen(data);
            // Load and display user status badges after welcome screen renders
            await loadUserStatus();
        } else {
            renderAccessDenied(data);
        }
        
    } catch (error) {
        console.error('Error initializing Mini App:', error);
        renderError('Network error. Please check your connection and try again.');
    }
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMiniApp);
} else {
    initMiniApp();
}
