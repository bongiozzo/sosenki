// SOSenki Mini App Client Logic

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand WebApp to full height
tg.expand();

// Ready the WebApp
tg.ready();

// Get app container
const appContainer = document.getElementById('app');

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Uncaught error:', event.error);
    renderError(
        'An unexpected error occurred',
        event.error
    );
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled rejection:', event.reason);
    renderError(
        'An unexpected error occurred',
        event.reason instanceof Error ? event.reason : new Error(String(event.reason))
    );
});

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
function renderError(message, error = null) {
    const template = document.getElementById('error-template');
    const content = template.content.cloneNode(true);
    
    // Set error message
    const errorMessageEl = content.getElementById('error-message');
    errorMessageEl.textContent = message || 'Please try again later.';
    
    // Collect debug info
    const debugInfo = {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        url: window.location.href,
        message: message,
        error: error ? {
            message: error.message,
            stack: error.stack,
            name: error.name
        } : null,
        telegramWebApp: {
            ready: tg.isExpanded,
            version: tg.version || 'unknown',
            platform: tg.platform || 'unknown',
            initData: tg.initData ? '✓ present' : '✗ missing'
        }
    };
    
    // Display debug info
    const debugInfoEl = content.getElementById('debug-info');
    debugInfoEl.textContent = JSON.stringify(debugInfo, null, 2);
    
    // Log to console
    console.error('Mini App Error:', debugInfo);
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
}

/**
 * Render user status badges from roles array
 * @param {Array<string>} roles - Array of role strings (e.g., ["investor", "owner"])
 */
function renderUserStatuses(roles) {
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
 * Load payment transactions from backend and render list
 */
async function loadPaymentTransactions() {
    try {
        const initData = tg.initData;
        
        if (!initData) {
            console.error('No Telegram init data available');
            return;
        }
        
        // Fetch payments from backend
        const response = await fetch('/api/mini-app/payments', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': initData,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error('Failed to load payments:', response.status, response.statusText);
            return;
        }
        
        const data = await response.json();
        
        // Render payment transactions
        if (data.payments && Array.isArray(data.payments)) {
            renderPaymentTransactions(data.payments);
        }
        
    } catch (error) {
        console.error('Error loading payment transactions:', error);
    }
}

/**
 * Render payment transactions list
 */
function renderPaymentTransactions(payments) {
    const container = document.getElementById('transaction-list');
    
    if (!container) {
        console.warn('Transaction list container not found');
        return;
    }
    
    container.innerHTML = '';
    
    if (!payments || payments.length === 0) {
        container.innerHTML = '<div class="transaction-empty">No transactions yet</div>';
        return;
    }
    
    payments.forEach(payment => {
        const transactionItem = document.createElement('div');
        transactionItem.className = 'transaction-item';
        
        // Left section: date and account
        const leftDiv = document.createElement('div');
        leftDiv.className = 'transaction-item-left';
        
        const dateEl = document.createElement('div');
        dateEl.className = 'transaction-item-date';
        dateEl.textContent = payment.payment_date;
        
        const accountEl = document.createElement('div');
        accountEl.className = 'transaction-item-account';
        accountEl.textContent = payment.account_name;
        
        leftDiv.appendChild(dateEl);
        leftDiv.appendChild(accountEl);
        
        // Right section: amount and optional comment
        const rightDiv = document.createElement('div');
        rightDiv.className = 'transaction-item-right';
        
        const amountEl = document.createElement('div');
        amountEl.className = 'transaction-item-amount';
        // Format amount: remove trailing .00 and add thousand delimiters
        const amount = parseFloat(payment.amount);
        const formattedAmount = amount % 1 === 0 
            ? amount.toLocaleString('ru-RU')
            : amount.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
        amountEl.textContent = `₽${formattedAmount}`;
        
        rightDiv.appendChild(amountEl);
        
        if (payment.comment) {
            const commentEl = document.createElement('div');
            commentEl.className = 'transaction-item-comment';
            commentEl.title = payment.comment; // Show full comment on hover
            commentEl.textContent = payment.comment;
            rightDiv.appendChild(commentEl);
        }
        
        transactionItem.appendChild(leftDiv);
        transactionItem.appendChild(rightDiv);
        
        container.appendChild(transactionItem);
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

        // Determine if user is representing someone else
        const isRepresenting = data.representative_of !== null && data.represented_user_roles !== null;

        // Use represented user's roles if representing, otherwise use authenticated user's roles
        const rolesToDisplay = isRepresenting ? data.represented_user_roles : data.roles;
        if (rolesToDisplay && Array.isArray(rolesToDisplay)) {
            renderUserStatuses(rolesToDisplay);
        }

        // Use represented user's share percentage if representing, otherwise use authenticated user's
        const sharePercentageToDisplay = isRepresenting ? data.represented_user_share_percentage : data.share_percentage;
        const isOwner = sharePercentageToDisplay !== null; // Owner if share_percentage is 1 or 0 (not null)
        renderStakeholderLink(data.stakeholder_url || null, isOwner, sharePercentageToDisplay);

        // Load properties if user is an owner
        if (isOwner) {
            await loadProperties();
        } else {
            // Hide properties section if not an owner
            const container = document.getElementById('properties-container');
            if (container) {
                container.classList.remove('visible');
            }
        }

        // Render representative info (always call to ensure proper hiding when no data)
        renderRepresentativeInfo(data.representative_of || null);

    } catch (error) {
        console.error('Error loading user status:', error);
    }
}

/**
 * Render stakeholder link for owners only
 * @param {string|null} url - Stakeholder shares URL from backend (null if not owner or not configured)
 * @param {boolean} isOwner - Whether the user is an owner
 * @param {number|null} sharePercentage - Share percentage (1 for signed owner, 0 for unsigned owner, null for non-owner)
 */
function renderStakeholderLink(url, isOwner = false, sharePercentage = null) {
    const container = document.getElementById('stakeholder-link-container');
    if (!container) {
        console.warn('Stakeholder link container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Only render if user is owner
    if (!isOwner) {
        return;
    }
    
    // Create section for stakeholder status and link
    const section = document.createElement('div');
    section.className = 'stakeholder-section';
    
    // Create status element showing Signed or Not Signed
    const statusDiv = document.createElement('div');
    statusDiv.className = 'stakeholder-status';
    
    if (sharePercentage === 1) {
        // Signed owner
        statusDiv.classList.add('signed');
        statusDiv.textContent = 'Signed';
    } else if (sharePercentage === 0) {
        // Unsigned owner
        statusDiv.classList.add('not-signed');
        statusDiv.textContent = 'Not Signed';
    }
    
    section.appendChild(statusDiv);
    
    // Create link element if URL is provided
    if (url && url.trim() !== '') {
        const link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'stakeholder-link';
        link.textContent = 'View Stakeholder Shares';
        section.appendChild(link);
    }
    
    container.appendChild(section);
}

/**
 * Render representative info (if user represents someone)
 * @param {Object|null} representativeOf - Representative info object with user_id, name, telegram_id
 */
function renderRepresentativeInfo(representativeOf) {
    const container = document.getElementById('representative-info-container');
    if (!container) {
        console.warn('Representative info container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Only render if representative_of data exists
    if (!representativeOf || !representativeOf.name) {
        // Hide the container when there's no representative info
        container.style.display = 'none';
        return;
    }
    
    // Show the container when there is representative info
    container.style.display = 'flex';
    
    // Create one-liner: "Represents [Name]"
    const representsText = document.createElement('div');
    representsText.className = 'representative-info-text';
    representsText.textContent = `Represents ${representativeOf.name}`;
    
    container.appendChild(representsText);
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
            // Load and display payment transactions
            await loadPaymentTransactions();
        } else {
            renderAccessDenied(data);
        }
        
    } catch (error) {
        console.error('Error initializing Mini App:', error);
        renderError('Network error. Please check your connection and try again.');
    }
}

/**
 * Render properties list with hierarchical grouping (main properties and additional properties)
 * @param {Array<Object>} properties - Array of property objects
 */
function renderProperties(properties) {
    const container = document.getElementById('properties-container');
    const listContainer = document.getElementById('properties-list');

    if (!container || !listContainer) {
        console.warn('Properties container not found');
        return;
    }

    // Clear existing content
    listContainer.innerHTML = '';

    // Hide if no properties
    if (!properties || properties.length === 0) {
        container.classList.remove('visible');
        return;
    }

    // Show container if there are properties
    container.classList.add('visible');

    // Build property hierarchy: separate main properties from additional ones
    const mainProperties = properties.filter(p => !p.main_property_id)
        .sort((a, b) => a.id - b.id);
    const additionalProperties = properties.filter(p => p.main_property_id);
    
    // Create a map for quick lookup of additional properties by main_property_id
    const additionalMap = {};
    additionalProperties.forEach(prop => {
        if (!additionalMap[prop.main_property_id]) {
            additionalMap[prop.main_property_id] = [];
        }
        additionalMap[prop.main_property_id].push(prop);
    });
    
    // Sort additional properties within each group by ID
    Object.keys(additionalMap).forEach(mainId => {
        additionalMap[mainId].sort((a, b) => a.id - b.id);
    });

    // Helper function to create property item element
    function createPropertyElement(property, isAdditional = false) {
        const item = document.createElement('div');
        item.className = `property-item ${isAdditional ? 'is-additional-property' : 'is-main-property'}`;

        // Create info section
        const info = document.createElement('div');
        info.className = 'property-info';

        // Property name with parent indicator for additional properties
        const nameEl = document.createElement('div');
        nameEl.className = 'property-name';
        if (isAdditional) {
            nameEl.textContent = '└─ ' + property.property_name;
        } else {
            nameEl.textContent = property.property_name;
        }
        info.appendChild(nameEl);

        // Property type
        if (property.type) {
            const typeEl = document.createElement('div');
            typeEl.className = 'property-type';
            typeEl.textContent = property.type;
            info.appendChild(typeEl);
        }

        // Meta information (badges and additional info)
        const metaEl = document.createElement('div');
        metaEl.className = 'property-meta';

        if (!property.is_ready) {
            const readyBadge = document.createElement('span');
            readyBadge.className = 'property-badge not-ready';
            readyBadge.textContent = 'Not Ready';
            metaEl.appendChild(readyBadge);
        }

        if (property.is_for_tenant) {
            const tenantBadge = document.createElement('span');
            tenantBadge.className = 'property-badge tenant';
            tenantBadge.textContent = 'Tenant';
            metaEl.appendChild(tenantBadge);
        }

        if (property.share_weight) {
            const weightBadge = document.createElement('span');
            weightBadge.className = 'property-badge';
            weightBadge.textContent = `Weight: ${property.share_weight}`;
            metaEl.appendChild(weightBadge);
        }

        if (property.sale_price) {
            const priceBadge = document.createElement('span');
            priceBadge.className = 'property-badge';
            const price = parseFloat(property.sale_price);
            const formattedPrice = price % 1 === 0 
                ? price.toLocaleString('ru-RU')
                : price.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
            priceBadge.textContent = `₽${formattedPrice}`;
            metaEl.appendChild(priceBadge);
        }

        if (metaEl.children.length > 0) {
            info.appendChild(metaEl);
        }

        // Photo link (if available)
        if (property.photo_link) {
            const photoLinkEl = document.createElement('div');
            photoLinkEl.className = 'property-photo-link';
            const linkEl = document.createElement('a');
            linkEl.href = property.photo_link;
            linkEl.target = '_blank';
            linkEl.rel = 'noopener noreferrer';
            linkEl.textContent = 'View Photos';
            photoLinkEl.appendChild(linkEl);
            info.appendChild(photoLinkEl);
        }

        item.appendChild(info);
        return item;
    }

    // Render main properties and their additional properties
    console.log('Rendering properties - Main:', mainProperties.length, 'Additional groups:', Object.keys(additionalMap).length);
    
    mainProperties.forEach(mainProperty => {
        // Render main property
        const mainItem = createPropertyElement(mainProperty, false);
        listContainer.appendChild(mainItem);
        console.log('Rendered main property:', mainProperty.id, mainProperty.property_name);

        // Render additional properties under this main property
        const children = additionalMap[mainProperty.id] || [];
        children.forEach(additionalProperty => {
            const childItem = createPropertyElement(additionalProperty, true);
            listContainer.appendChild(childItem);
            console.log('  └─ Rendered additional property:', additionalProperty.id, additionalProperty.property_name);
        });
    });
    
    console.log('Total items rendered:', listContainer.children.length);
}

/**
 * Load properties from backend and render list
 */
async function loadProperties() {
    try {
        const initData = tg.initData;

        if (!initData) {
            console.error('No Telegram init data available');
            return;
        }

        // Fetch properties from backend
        const response = await fetch('/api/mini-app/properties', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': initData,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            if (response.status === 403) {
                // User is not an owner, hide properties section
                const container = document.getElementById('properties-container');
                if (container) {
                    container.classList.remove('visible');
                }
                return;
            }
            console.error('Failed to load properties:', response.status, response.statusText);
            return;
        }

        const data = await response.json();

        if (data.properties && Array.isArray(data.properties)) {
            renderProperties(data.properties);
        }

    } catch (error) {
        console.error('Error loading properties:', error);
    }
}

/**
 * Start the app when DOM is ready
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMiniApp);
} else {
    initMiniApp();
}
