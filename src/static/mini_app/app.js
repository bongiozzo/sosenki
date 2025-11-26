// SOSenki Mini App Client Logic

// ---------------------------------------------------------------------------
// Translations
// ---------------------------------------------------------------------------
let __translations = null;

/**
 * Load translations from backend API
 * @returns {Promise<Object>} Translations dictionary
 */
async function loadTranslations() {
    if (__translations) return __translations;
    
    try {
        const response = await fetch('/api/mini-app/translations');
        if (response.ok) {
            __translations = await response.json();
        } else {
            console.error('Failed to load translations:', response.status);
            __translations = {};
        }
    } catch (error) {
        console.error('Error loading translations:', error);
        __translations = {};
    }
    return __translations;
}

/**
 * Get translation for a key with optional placeholder substitution.
 * Falls back to key if translation not found.
 * @param {string} key - Translation key (e.g., "loading", "welcome_back")
 * @param {Object} params - Placeholder values for string formatting
 * @returns {string} Translated string
 */
function t(key, params = {}) {
    if (!__translations) {
        console.warn('Translations not loaded yet, using key as fallback:', key);
        return key;
    }
    
    let value = __translations[key];
    if (value === undefined) {
        console.warn('Translation key not found:', key);
        return key;
    }
    
    // Replace placeholders like {user_name} with provided values
    if (params && typeof value === 'string') {
        for (const [paramKey, paramValue] of Object.entries(params)) {
            value = value.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), paramValue);
        }
    }
    
    return value;
}

/**
 * Apply translations to all DOM elements with data-i18n attributes.
 * Call this after any template is rendered to the DOM.
 */
function applyTranslations() {
    // Handle data-i18n (text content)
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const translated = t(key);
        // Only update if translation exists (not returning the key as fallback)
        if (translated !== key) {
            el.textContent = translated;
        }
    });
    
    // Handle data-i18n-html (innerHTML for elements with HTML content like <code>)
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.getAttribute('data-i18n-html');
        const translated = t(key);
        if (translated !== key) {
            el.innerHTML = translated;
        }
    });
}

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand WebApp to full height
tg.expand();

// Ready the WebApp
tg.ready();

// Get app container
const appContainer = document.getElementById('app');

// ---------------------------------------------------------------------------
// Debug Console (temporary)
// ---------------------------------------------------------------------------
const debugConsole = document.getElementById('debug-console');
const debugConsoleOutput = document.getElementById('debug-console-output');

function addDebugLog(message) {
    if (!debugConsole || !debugConsoleOutput) return;
    
    debugConsole.style.display = 'block';
    const logDiv = document.createElement('div');
    logDiv.style.marginBottom = '4px';
    logDiv.style.wordBreak = 'break-all';
    logDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    debugConsoleOutput.appendChild(logDiv);
    debugConsoleOutput.scrollTop = debugConsoleOutput.scrollHeight;
}

// Override console.log and console.error
const originalLog = console.log;
const originalError = console.error;
console.log = function(...args) {
    originalLog.apply(console, args);
    addDebugLog(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
};
console.error = function(...args) {
    originalError.apply(console, args);
    addDebugLog('ERROR: ' + args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
};

// ---------------------------------------------------------------------------
// Unified App Context (authenticated vs represented user)
// ---------------------------------------------------------------------------
let __appContext = null; // memoized context
let __selectedUserId = null; // admin-selected user ID (takes precedence)
let __authenticatedUserInfo = null; // Keep authenticated user info constant (name, isAdmin)
let __currentAccountId = null; // Current account ID for endpoint calls
let __previousPage = 'welcome'; // Navigation stack: 'welcome', 'accounts', 'transactions'

/**
 * Get selected user ID from URL hash parameter
 * @returns {number|null} User ID from hash or null
 */
function getSelectedUserIdFromUrl() {
    const hash = window.location.hash;
    const match = hash.match(/selected_user=(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}

/**
 * Set selected user ID in URL hash parameter
 * @param {number} userId - User ID to store in hash
 */
function setSelectedUserIdInUrl(userId) {
    // Preserve existing tgWebAppData in hash, add/update selected_user parameter
    const hash = window.location.hash;
    const parts = hash.split('&');
    
    // Remove existing selected_user parameter
    const filtered = parts.filter(p => !p.includes('selected_user='));
    
    // Add new selected_user parameter
    filtered.push(`selected_user=${userId}`);
    
    window.location.hash = filtered.join('&');
}

async function getAppContext(selectedUserId = null) {
    // If selectedUserId provided, always refresh context
    if (selectedUserId !== null) {
        __selectedUserId = selectedUserId;
        __appContext = null;
    }
    
    // On first load, check URL hash for persisted selection
    if (__selectedUserId === null && __appContext === null) {
        const urlSelectedUserId = getSelectedUserIdFromUrl();
        if (urlSelectedUserId !== null) {
            __selectedUserId = urlSelectedUserId;
        }
    }
    
    if (__appContext) return __appContext;
    const initData = getInitData();
    if (!initData) {
        console.error('[context] Missing initData');
        return null;
    }
    try {
        // Build URL with selected_user_id if present
        let url = '/api/mini-app/user-status';
        if (__selectedUserId !== null) {
            url += `?selected_user_id=${__selectedUserId}`;
        }
        
        const resp = await fetchWithTmaAuth(url, initData);
        if (!resp.ok) {
            console.error('[context] user-status failed', resp.status, resp.statusText);
            return null;
        }
        const data = await resp.json();
        const isRepresenting = !!(data.representative_of && data.represented_user_roles);
        const roles = (isRepresenting ? data.represented_user_roles : data.roles) || [];
        const sharePercentage = isRepresenting ? data.represented_user_share_percentage : data.share_percentage;
        const isOwner = sharePercentage !== null;
        const isAdministrator = (data.roles || []).includes('administrator');
        
        // Extract and store account_id for endpoint calls
        __currentAccountId = data.account_id || null;
        
        __appContext = {
            isRepresenting,
            isAdministrator,
            authenticatedUserId: data.user_id,
            roles,
            isOwner,
            sharePercentage,
            stakeholderUrl: data.stakeholder_url || null,
            representativeOf: data.representative_of || null,
            greetingName: data.authenticated_user_name || data.authenticated_first_name || 'User'
        };
        console.log('[getAppContext] Context retrieved:', __appContext);
        console.log('[getAppContext] Current account ID:', __currentAccountId);
        return __appContext;
    } catch (e) {
        console.error('[context] Exception', e);
        return null;
    }
}

function refreshAppContext() { __appContext = null; }

/**
 * Extract initData - works on both Desktop and iOS
 * On iOS, Telegram may pass initData in URL hash instead of WebApp property
 */
function getInitData() {
    // First try standard WebApp property (works on desktop)
    if (tg.initData && tg.initData.trim()) {
        return tg.initData;
    }
    
    // Fallback: Try to extract from URL hash (iOS)
    // On iOS, the hash looks like: #tgWebAppData=query_id%3D...%26user%3D...
    const hash = window.location.hash;
    const match = hash.match(/tgWebAppData=([^&]*)/);
    if (match && match[1]) {
        try {
            const encodedData = match[1];
            const decodedData = decodeURIComponent(encodedData);
            return decodedData;
        } catch (e) {
            return null;
        }
    }
    return null;
}

/**
 * Fetch helper using Telegram Mini Apps recommended transport.
 * Sends POST with Authorization: "tma <initData>" and falls back to GET with X header.
 */
async function fetchWithTmaAuth(url, initData) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': 'tma ' + initData,
        },
    });
}

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
    
    // Apply translations to rendered template
    applyTranslations();
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
    
    // Apply translations to rendered template
    applyTranslations();
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
    
    // Collect comprehensive debug info
    const debugInfo = {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        url: window.location.href,
        urlHash: window.location.hash ? window.location.hash.substring(0, 200) : 'empty',
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
            initData: tg.initData ? `✓ present (${tg.initData.length} chars)` : '✗ missing',
            initDataUnsafe: tg.initDataUnsafe ? JSON.stringify(tg.initDataUnsafe).substring(0, 200) : 'null'
        },
        network: {
            online: navigator.onLine,
            connectionType: navigator.connection?.effectiveType || 'unknown'
        },
        browserCapabilities: {
            fetchAvailable: typeof fetch !== 'undefined',
            headersAvailable: typeof Headers !== 'undefined',
            corsSupported: true
        }
    };
    
    // Display debug info
    const debugInfoEl = content.getElementById('debug-info');
    debugInfoEl.textContent = JSON.stringify(debugInfo, null, 2);
    
    // Store debug info globally for copy function
    window.currentDebugInfo = JSON.stringify(debugInfo, null, 2);
    
    // Log to console
    console.error('Mini App Error:', debugInfo);
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    
    // Apply translations to rendered template
    applyTranslations();
}

/**
 * Copy debug info to clipboard
 */
function copyDebugInfo() {
    if (!window.currentDebugInfo) {
        alert(t('no_data'));
        return;
    }
    
    navigator.clipboard.writeText(window.currentDebugInfo).then(() => {
        alert(t('copied'));
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert(t('copy_failed'));
    });
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
 * Format date to locale string (e.g., "19 нояб. 2025")
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format amount with 2 decimal places and locale-specific formatting
 */
function formatAmount(amount) {
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Load and render transactions from backend
 * @param {string} containerId - ID of container to render transactions into
 * @param {string} scope - Scope for filtering ('personal' or 'all'). Defaults to 'personal'
 * @param {boolean} isRepresenting - Whether the authenticated user is representing someone else
 */
async function loadTransactions(containerId = 'transactions-list', scope = 'personal', contextOrFlag = false) {
    try {
        const initData = getInitData();
        
        if (!initData) {
            return;
        }

        if (!__currentAccountId) {
            console.warn('Account ID not available, cannot load transactions');
            return;
        }
        
        // Build URL with account_id parameter
        let url = `/api/mini-app/transactions-list?account_id=${__currentAccountId}&scope=${scope}`;
        
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        
        // Render transactions
        if (data.transactions && Array.isArray(data.transactions)) {
            renderTransactionsList(data.transactions, containerId);
        }
        
    } catch (error) {
        // Error silently handled
    }
}

/**
 * Render transactions list into specified container
 * @param {Array} transactions - Array of transaction objects
 * @param {string} containerId - ID of container to render into
 */
function renderTransactionsList(transactions, containerId = 'transactions-list') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.warn(`Transaction list container '${containerId}' not found`);
        return;
    }
    
    container.innerHTML = '';
    
    if (!transactions || transactions.length === 0) {
        container.innerHTML = `<div class="transaction-empty">${t('no_transactions')}</div>`;
        return;
    }
    
    transactions.forEach(transaction => {
        const transactionItem = document.createElement('div');
        transactionItem.className = 'transaction-item';
        
        // Header row: date and accounts with amount
        const headerDiv = document.createElement('div');
        headerDiv.className = 'transaction-item-header';
        
        const leftDiv = document.createElement('div');
        leftDiv.className = 'transaction-item-left';
        
        const dateEl = document.createElement('div');
        dateEl.className = 'transaction-item-date';
        dateEl.textContent = formatDate(transaction.date);
        
        const accountEl = document.createElement('div');
        accountEl.className = 'transaction-item-account';
        
        // Create clickable account links if account IDs are available
        if (transaction.from_account_id && transaction.to_account_id) {
            const fromLink = document.createElement('a');
            fromLink.href = '#';
            fromLink.className = 'account-link';
            fromLink.textContent = transaction.from_ac_name;
            fromLink.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                navigateToAccountDetails(transaction.from_account_id, transaction.from_ac_name, 'transactions');
            };
            
            const arrowSpan = document.createElement('span');
            arrowSpan.textContent = ' → ';
            
            const toLink = document.createElement('a');
            toLink.href = '#';
            toLink.className = 'account-link';
            toLink.textContent = transaction.to_ac_name;
            toLink.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                navigateToAccountDetails(transaction.to_account_id, transaction.to_ac_name, 'transactions');
            };
            
            accountEl.appendChild(fromLink);
            accountEl.appendChild(arrowSpan);
            accountEl.appendChild(toLink);
        } else {
            // Fallback to plain text if IDs not available
            accountEl.textContent = `${transaction.from_ac_name} → ${transaction.to_ac_name}`;
        }
        
        leftDiv.appendChild(dateEl);
        leftDiv.appendChild(accountEl);
        
        const amountEl = document.createElement('div');
        amountEl.className = 'transaction-item-amount';
        amountEl.textContent = `₽${formatAmount(transaction.amount)}`;
        
        headerDiv.appendChild(leftDiv);
        headerDiv.appendChild(amountEl);
        
        transactionItem.appendChild(headerDiv);
        
        // Description line (if exists)
        if (transaction.description) {
            const descriptionEl = document.createElement('div');
            descriptionEl.className = 'transaction-item-description';
            descriptionEl.textContent = transaction.description;
            transactionItem.appendChild(descriptionEl);
        }
        
        container.appendChild(transactionItem);
    });
}

/**
 * Load and render bills from backend
 * @param {string} containerId - ID of container to render bills into
 * @param {boolean} isRepresenting - Whether the authenticated user is representing someone else
 */
async function loadBills(containerId = 'bills-list', contextOrFlag = false) {
    try {
        const initData = getInitData();
        
        if (!initData) {
            return;
        }

        if (!__currentAccountId) {
            console.warn('Account ID not available, cannot load bills');
            return;
        }
        
        // Build URL with account_id parameter
        let url = `/api/mini-app/bills?account_id=${__currentAccountId}`;
        
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        
        // Render bills
        if (data.bills && Array.isArray(data.bills)) {
            renderBills(data.bills, containerId);
        }
        
    } catch (error) {
        // Error silently handled
    }
}

/**
 * Render bills list into specified container (all bill types)
 * @param {Array} bills - Array of bill objects
 * @param {string} containerId - ID of container to render into
 */
function renderBills(bills, containerId = 'bills-list') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.warn(`Bills container '${containerId}' not found`);
        return;
    }
    
    container.innerHTML = '';
    
    if (!bills || bills.length === 0) {
        container.innerHTML = `<div class="bill-empty">${t('no_bills')}</div>`;
        return;
    }
    
    bills.forEach(bill => {
        const billItem = document.createElement('div');
        billItem.className = 'bill-item';
        
        // Line 1: Period dates (from - to)
        const periodDiv = document.createElement('div');
        periodDiv.className = 'bill-item-period-row';
        const periodEl = document.createElement('div');
        periodEl.className = 'bill-item-period';
        periodEl.textContent = `${formatDate(bill.period_start_date)} - ${formatDate(bill.period_end_date)}`;
        periodDiv.appendChild(periodEl);
        billItem.appendChild(periodDiv);
        
        // Line 2: Bill type, Property, Amount
        const typePropertyRowDiv = document.createElement('div');
        typePropertyRowDiv.className = 'bill-item-type-property-row';
        
        // Bill type badge (left)
        const badgeEl = document.createElement('span');
        badgeEl.className = `bill-type-badge bill-type-${bill.bill_type.toLowerCase()}`;
        badgeEl.textContent = formatBillType(bill.bill_type);
        typePropertyRowDiv.appendChild(badgeEl);
        
        // Property info (center)
        const propertyLeftDiv = document.createElement('div');
        propertyLeftDiv.className = 'bill-item-property-center';
        
        if (bill.property_name || bill.property_type || bill.comment) {
            const propertyEl = document.createElement('div');
            propertyEl.className = 'bill-item-property';
            
            if (bill.property_name) {
                propertyEl.textContent = bill.property_name;
            } else if (bill.comment) {
                propertyEl.textContent = bill.comment;
            }
            
            propertyLeftDiv.appendChild(propertyEl);
        }
        
        typePropertyRowDiv.appendChild(propertyLeftDiv);
        
        // Amount (right)
        const amountEl = document.createElement('div');
        amountEl.className = 'bill-item-amount';
        amountEl.textContent = `₽${formatAmount(bill.bill_amount)}`;
        
        typePropertyRowDiv.appendChild(amountEl);
        billItem.appendChild(typePropertyRowDiv);
        
        // Readings row (only for ELECTRICITY bills with end_reading)
        if (bill.bill_type && bill.bill_type.toUpperCase() === 'ELECTRICITY' && bill.end_reading !== null) {
            const readingsDiv = document.createElement('div');
            readingsDiv.className = 'bill-item-readings';
            
            const readingsText = document.createElement('span');
            readingsText.className = 'readings-range';
            
            // Display start → end if both exist, otherwise just end
            if (bill.start_reading !== null) {
                readingsText.textContent = `${formatAmount(bill.start_reading)} → ${formatAmount(bill.end_reading)}`;
            } else {
                readingsText.textContent = `${formatAmount(bill.end_reading)} kWh`;
            }
            
            readingsDiv.appendChild(readingsText);
            
            // Add consumption badge if available
            if (bill.consumption !== null) {
                const consumptionBadge = document.createElement('span');
                consumptionBadge.className = 'consumption-badge';
                consumptionBadge.textContent = `${formatAmount(bill.consumption)} kWh`;
                readingsDiv.appendChild(consumptionBadge);
            }
            
            billItem.appendChild(readingsDiv);
        }
        
        container.appendChild(billItem);
    });
}

/**
 * Format bill type for display
 * @param {string} billType - Bill type (electricity, shared_electricity, conservation, main or uppercase variants)
 * @returns {string} Formatted display string
 */
function formatBillType(billType) {
    const normalized = billType.toUpperCase();
    const typeMap = {
        'ELECTRICITY': t('bill_electricity'),
        'SHARED_ELECTRICITY': t('bill_shared_electricity'),
        'CONSERVATION': t('bill_conservation'),
        'MAIN': t('bill_main')
    };
    return typeMap[normalized] || billType;
}

/**
 * Load user status from backend and render badges
 */
async function loadUserStatus() { // legacy path retained; unified context used in initMiniApp
    try {
        const initData = getInitData();

        if (!initData) {
            return;
        }

        // Fetch user status from backend
        const response = await fetchWithTmaAuth('/api/mini-app/user-status', initData);
        
        if (!response.ok) {
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
            await loadProperties(isRepresenting);
        } else {
            // Hide properties section if not an owner
            const container = document.getElementById('properties-container');
            if (container) {
                container.classList.remove('visible');
            }
        }

        // Render representative info (always call to ensure proper hiding when no data)
        renderRepresentativeInfo(data.representative_of || null);
        
        // Datasets now loaded via getAppContext() inside initMiniApp.

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
    console.log('[renderStakeholderLink] url:', url, 'isOwner:', isOwner, 'sharePercentage:', sharePercentage);
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
        statusDiv.textContent = t('signed');
    } else if (sharePercentage === 0) {
        // Unsigned owner
        statusDiv.classList.add('not-signed');
        statusDiv.textContent = t('not_signed');
    }
    
    section.appendChild(statusDiv);
    
    // Create link element if URL is provided
    if (url && url.trim() !== '') {
        const link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'stakeholder-link';
        link.textContent = t('view_stakeholder_shares');
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
    representsText.textContent = t('represents', { name: representativeOf.name });
    
    container.appendChild(representsText);
}

/**
 * Fetch all users from backend (admin only)
 * @returns {Promise<Array>} Array of user objects
 */
async function fetchAllUsers() {
    try {
        const initData = getInitData();
        if (!initData) {
            console.error('No init data for fetching users');
            return [];
        }
        
        const response = await fetchWithTmaAuth('/api/mini-app/users', initData);
        
        if (!response.ok) {
            console.error('Failed to fetch users:', response.status);
            return [];
        }
        
        const data = await response.json();
        return data.users || [];
    } catch (error) {
        console.error('Error fetching users:', error);
        return [];
    }
}

/**
 * Render admin user selector dropdown
 * @param {boolean} isAdministrator - Whether authenticated user is admin
 * @param {number} authenticatedUserId - ID of authenticated user (for default selection)
 */
async function renderAdminUserSelector(isAdministrator, authenticatedUserId) {
    const container = document.getElementById('representative-info-container');
    if (!container) {
        console.warn('Representative info container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Only render for administrators
    if (!isAdministrator) {
        container.style.display = 'none';
        return;
    }
    
    // Show container
    container.style.display = 'flex';
    
    // Fetch all users
    const users = await fetchAllUsers();
    
    if (users.length === 0) {
        console.warn('No users available for admin selector');
        container.style.display = 'none';
        return;
    }
    
    // Create dropdown wrapper
    const selectorDiv = document.createElement('div');
    selectorDiv.className = 'admin-user-selector';
    
    // Create label
    const label = document.createElement('label');
    label.textContent = t('view_as');
    label.setAttribute('for', 'admin-user-select');
    selectorDiv.appendChild(label);
    
    // Create select element
    const select = document.createElement('select');
    select.id = 'admin-user-select';
    
    // Add options
    users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.user_id;
        option.textContent = user.name;
        
        // Pre-select current user (authenticated or admin-selected)
        const currentUserId = __selectedUserId !== null ? __selectedUserId : authenticatedUserId;
        if (user.user_id === currentUserId) {
            option.selected = true;
        }
        
        select.appendChild(option);
    });
    
    // Add change handler
    select.addEventListener('change', async (event) => {
        const selectedUserId = parseInt(event.target.value, 10);
        
        // Update global selected user ID and persist in URL
        __selectedUserId = selectedUserId;
        setSelectedUserIdInUrl(selectedUserId);
        refreshAppContext();
        
        // Get updated context for selected user
        const updatedContext = await getAppContext(selectedUserId);
        
        if (updatedContext) {
            // Reload all datasets with the new context
            await reloadAllDatasets(updatedContext);
        }
    });
    
    selectorDiv.appendChild(select);
    container.appendChild(selectorDiv);
}

/**
 * Handle menu item click
 */
async function handleMenuAction(action) {
    if (action === 'enjoy') {
        try {
            const initData = getInitData();
            if (!initData) {
                tg.showAlert(t('auth_failed'));
                return;
            }
            
            // Fetch photo gallery URL from backend config
            const response = await fetchWithTmaAuth('/api/mini-app/config', initData);
            const data = await response.json();
            
            if (data.photoGalleryUrl) {
                // Open external browser with photo gallery URL
                tg.openLink(data.photoGalleryUrl);
            } else {
                tg.showAlert(t('gallery_not_configured'));
            }
        } catch (error) {
            console.error('Error fetching config:', error);
            tg.showAlert(t('gallery_error'));
        }
        return;
    }
    
    // Show Telegram alert for other features (placeholder)
    tg.showAlert(t('feature_coming_soon', { action: action }));
    
    // In future: POST to /api/mini-app/menu-action
}

/**
 * Reload all datasets (statuses, stakeholder link, properties, balance, transactions, bills)
 * Used when context changes (admin switch or representing user change)
 * @param {Object} context - App context object with all user info
 */
async function reloadAllDatasets(context) {
    if (!context) return;
    
    // Render static data first (no backend calls needed)
    renderUserStatuses(context.roles);
    renderStakeholderLink(context.stakeholderUrl, context.isOwner, context.sharePercentage);
    
    // Reload dynamic data from backend
    if (context.isOwner) {
        await loadProperties(context);
        await loadBalance(context);
    } else {
        // Hide properties and balance if not owner
        const propsContainer = document.getElementById('properties-container');
        if (propsContainer) {
            propsContainer.classList.remove('visible');
        }
        const balanceContainer = document.getElementById('balance-container');
        if (balanceContainer) {
            balanceContainer.classList.remove('visible');
        }
    }
    
    // Load transactions and bills
    await loadTransactions('transactions-list', 'personal', context);
    await loadBills('bills-list', context);
}

/**
 * Navigate to transactions page
 */
function navigateToTransactions(event) {
    event.preventDefault();
    __previousPage = 'welcome';
    
    // Show transactions page
    const template = document.getElementById('transactions-template');
    if (!template) {
        console.error('Transactions template not found');
        return;
    }
    
    const content = template.content.cloneNode(true);
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    
    // Apply translations to rendered template
    applyTranslations();
    
    // Load all organization transactions
    loadTransactions('transactions-list', 'all');
}

/**
 * Go back to welcome screen
 */
function goBackToWelcome() {
    // Reload to show welcome screen again
    location.reload();
}

/**
 * Navigate to account details page
 * @param {number} accountId - Account ID to show details for
 * @param {string} accountName - Account name for header
 * @param {string} fromPage - Source page for back navigation ('welcome', 'accounts', 'transactions')
 */
function navigateToAccountDetails(accountId, accountName, fromPage = 'accounts') {
    __previousPage = fromPage;
    
    // Show account details page
    const template = document.getElementById('account-details-template');
    if (!template) {
        console.error('Account details template not found');
        return;
    }
    
    const content = template.content.cloneNode(true);
    
    // Set account name in header
    const nameEl = content.getElementById('account-details-name');
    if (nameEl) {
        nameEl.textContent = accountName;
    }
    
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    
    // Apply translations to rendered template
    applyTranslations();
    
    // Load account data
    loadAccountDetails(accountId);
}

/**
 * Go back from account details page
 */
function goBackFromAccountDetails() {
    if (__previousPage === 'accounts') {
        // Go back to accounts list
        const event = { preventDefault: () => {} };
        navigateToAccounts(event);
    } else if (__previousPage === 'transactions') {
        // Go back to transactions list
        const event = { preventDefault: () => {} };
        navigateToTransactions(event);
    } else {
        // Default: go back to welcome
        goBackToWelcome();
    }
}

/**
 * Load all data for account details page
 * @param {number} accountId - Account ID to load
 */
async function loadAccountDetails(accountId) {
    try {
        const initData = getInitData();
        if (!initData) return;
        
        // Load balance
        const balanceUrl = `/api/mini-app/balance?account_id=${accountId}`;
        const balanceResp = await fetchWithTmaAuth(balanceUrl, initData);
        if (balanceResp.ok) {
            const balanceData = await balanceResp.json();
            // Render balance with inversion for account details page
            const displayBalance = balanceData.invert_for_display ? -balanceData.balance : balanceData.balance;
            const balanceEl = document.getElementById('account-balance-value');
            if (balanceEl) {
                const formattedBalance = formatAmount(Math.abs(displayBalance));
                const balanceClass = displayBalance >= 0 ? 'positive' : 'negative';
                balanceEl.className = `balance-value ${balanceClass}`;
                balanceEl.textContent = `${displayBalance >= 0 ? '+' : '-'}₽${formattedBalance}`;
            }
        }
        
        // Load transactions for this account
        const transUrl = `/api/mini-app/transactions-list?account_id=${accountId}&scope=personal`;
        const transResp = await fetchWithTmaAuth(transUrl, initData);
        if (transResp.ok) {
            const transData = await transResp.json();
            if (transData.transactions && Array.isArray(transData.transactions)) {
                renderTransactionsList(transData.transactions, 'account-transactions-list');
            }
        }
        
        // Load bills for this account
        const billsUrl = `/api/mini-app/bills?account_id=${accountId}`;
        const billsResp = await fetchWithTmaAuth(billsUrl, initData);
        if (billsResp.ok) {
            const billsData = await billsResp.json();
            if (billsData.bills && Array.isArray(billsData.bills)) {
                renderBills(billsData.bills, 'account-bills-list');
            }
        }
    } catch (error) {
        console.error('Error loading account details:', error);
    }
}

/**
 * Initialize Mini App
 */
/**
 * Load and render balance from backend
 * @param {boolean} isRepresenting - Whether the authenticated user is representing someone else
 */
async function loadBalance(contextOrFlag = false) {
    try {
        const initData = getInitData();
        
        if (!initData) {
            return;
        }

        if (!__currentAccountId) {
            console.warn('Account ID not available, cannot load balance');
            return;
        }
        
        // Build URL with account_id parameter
        let url = `/api/mini-app/balance?account_id=${__currentAccountId}`;
        
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        
        if (data.balance !== undefined) {
            renderBalance(data.balance, data.invert_for_display || false);
        }
        
    } catch (error) {
        // Error silently handled
    }
}

/**
 * Render balance into the balance-container
 * @param {number} balance - Balance amount (raw value)
 * @param {boolean} invert - Whether to invert the display value (for OWNER accounts)
 * @param {string} containerId - Optional container ID (defaults to 'balance-container')
 */
function renderBalance(balance, invert = false, containerId = 'balance-container') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.warn('Balance container not found:', containerId);
        return;
    }
    
    // Show the balance section
    container.classList.add('visible');
    
    // Apply inversion for display (OWNER accounts show inverted balance)
    const displayBalance = invert ? -balance : balance;
    
    // Find the balance-value element and update it
    const balanceValue = container.querySelector('.balance-value') || document.getElementById(containerId.replace('-container', '-value'));
    if (balanceValue) {
        const formattedBalance = formatAmount(Math.abs(displayBalance));
        const balanceClass = displayBalance >= 0 ? 'positive' : 'negative';
        balanceValue.className = `balance-value ${balanceClass}`;
        balanceValue.textContent = `${displayBalance >= 0 ? '+' : '-'}₽${formattedBalance}`;
    }
}

/**
 * Navigate to accounts page
 */
function navigateToAccounts(event) {
    event.preventDefault();
    __previousPage = 'welcome';

    // Show accounts page
    const template = document.getElementById('accounts-template');
    if (!template) {
        return;
    }
    
    const content = template.content.cloneNode(true);
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    
    // Apply translations to rendered template
    applyTranslations();
    
    // Load all accounts
    loadAccounts('accounts-list');
}

/**
 * Load and render accounts from backend
 * @param {string} containerId - ID of container to render accounts into
 */
function loadAccounts(containerId = 'accounts-list') {
    try {
        const initData = getInitData();
        
        if (!initData) {
            return;
        }

        // Fetch accounts from backend (all users, info available to any owner)
        const url = `/api/mini-app/accounts`;
        
        fetchWithTmaAuth(url, initData)
            .then(response => {
                if (!response.ok) {
                    return response.text().then(errorText => {
                        throw new Error(`HTTP ${response.status}`);
                    });
                }
                
                return response.json();
            })
            .then(data => {
                renderAccountsPage(data.accounts || [], containerId);
            })
            .catch(error => {
                // Error silently handled
            });
        
    } catch (error) {
        // Error silently handled
    }
}

/**
 * Render accounts page with list of accounts and their balances
 * @param {Array} accounts - Array of account items {account_name, account_type, balance}
 * @param {string} containerId - ID of container to render into
 */
function renderAccountsPage(accounts, containerId = 'accounts-list') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        return;
    }
    
    container.innerHTML = '';
    
    if (!accounts || accounts.length === 0) {
        container.innerHTML = `<div class="account-empty">${t('no_accounts')}</div>`;
        return;
    }
    
    // Sort: Owners first (biggest debt), then Organization, then Staff
    const sorted = [...accounts].sort((a, b) => {
        // Define type priority: owner (0), organization (1), staff (2)
        const typePriority = { 'owner': 0, 'organization': 1, 'staff': 2 };
        const aPriority = typePriority[a.account_type] ?? 3;
        const bPriority = typePriority[b.account_type] ?? 3;
        
        // First, sort by type priority
        if (aPriority !== bPriority) {
            return aPriority - bPriority;
        }
        
        // Within same type, for owners sort by biggest debt (most positive balance after inversion)
        // For others, sort by balance descending (most positive first)
        if (a.account_type === 'owner') {
            // For owners: invert_for_display means we show -balance, so sort by raw balance descending (most positive = most debt when displayed)
            return b.balance - a.balance;
        }
        
        // For organization and staff, sort by balance descending
        return b.balance - a.balance;
    });
    
    sorted.forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'account-row clickable';
        row.style.cursor = 'pointer';
        
        // Make row clickable to navigate to account details
        row.onclick = () => {
            navigateToAccountDetails(item.account_id, item.account_name, 'accounts');
        };
        
        // Account info (icon + name)
        const infoDiv = document.createElement('div');
        infoDiv.className = 'account-row-info';
        
        // Type icon based on account type (organization, owner, staff)
        const iconEl = document.createElement('span');
        iconEl.className = 'account-row-icon';
        if (item.account_type === 'organization') {
            iconEl.textContent = '🏦';
        } else if (item.account_type === 'staff') {
            iconEl.textContent = '👷';
        } else {
            iconEl.textContent = '👤';
        }
        infoDiv.appendChild(iconEl);
        
        const nameEl = document.createElement('div');
        nameEl.className = 'account-row-name';
        nameEl.textContent = item.account_name;
        infoDiv.appendChild(nameEl);
        
        row.appendChild(infoDiv);
        
        // Balance amount (with color coding and inversion for owner accounts)
        const displayBalance = item.invert_for_display ? -item.balance : item.balance;
        const amountEl = document.createElement('div');
        const formattedAmount = formatAmount(Math.abs(displayBalance));
        const balanceClass = displayBalance >= 0 ? 'positive' : 'negative';
        amountEl.className = `account-row-amount ${balanceClass}`;
        amountEl.textContent = `${displayBalance >= 0 ? '+' : '-'}₽${formattedAmount}`;
        
        row.appendChild(amountEl);
        container.appendChild(row);
    });
}

async function initMiniApp() {
    try {
        // Load translations first
        await loadTranslations();
        
        // Get init data from Telegram WebApp (supports both desktop and iOS)
        const initData = getInitData();
        
        if (!initData) {
            renderError(t('auth_failed'));
            return;
        }
        
        try {
            // Call backend API to check registration status
            const response = await fetchWithTmaAuth('/api/mini-app/init', initData);
            
            if (!response.ok) {
                const errorText = await response.text();
                if (response.status === 401) {
                    renderError(t('auth_restart'));
                } else {
                    renderError(t('server_error'));
                }
                return;
            }
            
            const data = await response.json();
            
            // Render appropriate screen based on registration status
            if (data.isRegistered) {
                renderWelcomeScreen(data);
                
                // Get initial context (will restore selected_user_id from URL if present)
                const context = await getAppContext();
                if (context) {
                    // Store authenticated user info (constant throughout session)
                    // Note: context.isAdministrator is for the SELECTED user, we need the AUTH user's admin status
                    // Get authenticated user's roles from the initial context
                    const initAuthUserResponse = await fetchWithTmaAuth('/api/mini-app/user-status', initData);
                    const authUserData = await initAuthUserResponse.json();
                    const isAuthUserAdmin = (authUserData.roles || []).includes('administrator');
                    
                    __authenticatedUserInfo = {
                        isAdministrator: isAuthUserAdmin,
                        name: context.greetingName
                    };
                    
                    // Render admin dropdown OR representative info (dropdown takes precedence, always shown if auth user is admin)
                    if (__authenticatedUserInfo.isAdministrator) {
                        await renderAdminUserSelector(__authenticatedUserInfo.isAdministrator, authUserData.user_id);
                    } else {
                        renderRepresentativeInfo(context.representativeOf);
                    }
                    
                    // Load all datasets with context (either selected user or authenticated user)
                    await reloadAllDatasets(context);
                }
            } else {
                renderAccessDenied(data);
            }
            
        } catch (fetchError) {
            throw fetchError; // Re-throw to outer catch
        }
        
    } catch (error) {
        renderError(t('network_error'));
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
            readyBadge.textContent = t('not_ready');
            metaEl.appendChild(readyBadge);
        }

        if (property.is_for_tenant) {
            const tenantBadge = document.createElement('span');
            tenantBadge.className = 'property-badge tenant';
            tenantBadge.textContent = t('tenant');
            metaEl.appendChild(tenantBadge);
        }

        if (property.share_weight) {
            const weightBadge = document.createElement('span');
            weightBadge.className = 'property-badge';
            weightBadge.textContent = `${t('weight')}: ${property.share_weight}`;
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
            linkEl.textContent = t('view_photos');
            photoLinkEl.appendChild(linkEl);
            info.appendChild(photoLinkEl);
        }

        item.appendChild(info);
        return item;
    }

    // Render main properties and their additional properties
    mainProperties.forEach(mainProperty => {
        // Render main property
        const mainItem = createPropertyElement(mainProperty, false);
        listContainer.appendChild(mainItem);

        // Render additional properties under this main property
        const children = additionalMap[mainProperty.id] || [];
        children.forEach(additionalProperty => {
            const childItem = createPropertyElement(additionalProperty, true);
            listContainer.appendChild(childItem);
        });
    });
}

/**
 * Load properties from backend and render list
 */
async function loadProperties(contextOrFlag = false) {
    try {
        const initData = getInitData();

        if (!initData) {
            console.error('No Telegram init data available');
            return;
        }

        const isRepresenting = (typeof contextOrFlag === 'object') ? !!contextOrFlag.isRepresenting : !!contextOrFlag;
        
        // Build URL with parameters
        let url = `/api/mini-app/properties?representing=${isRepresenting}`;
        if (__selectedUserId !== null) {
            url += `&selected_user_id=${__selectedUserId}`;
        }
        
        const response = await fetchWithTmaAuth(url, initData);

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
