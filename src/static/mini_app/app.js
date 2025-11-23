// SOSenki Mini App Client Logic

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand WebApp to full height
tg.expand();

// Ready the WebApp
tg.ready();

// Get app container
const appContainer = document.getElementById('app');

// ---------------------------------------------------------------------------
// Unified App Context (authenticated vs represented user)
// ---------------------------------------------------------------------------
let __appContext = null; // memoized context

async function getAppContext() {
    if (__appContext) return __appContext;
    const initData = getInitData();
    if (!initData) {
        console.error('[context] Missing initData');
        return null;
    }
    try {
        const resp = await fetchWithTmaAuth('/api/mini-app/user-status', initData);
        if (!resp.ok) {
            console.error('[context] user-status failed', resp.status, resp.statusText);
            return null;
        }
        const data = await resp.json();
        const isRepresenting = !!(data.representative_of && data.represented_user_roles);
        const roles = (isRepresenting ? data.represented_user_roles : data.roles) || [];
        const sharePercentage = isRepresenting ? data.represented_user_share_percentage : data.share_percentage;
        const isOwner = sharePercentage !== null;
        __appContext = {
            isRepresenting,
            roles,
            isOwner,
            sharePercentage,
            stakeholderUrl: data.stakeholder_url || null,
            representativeOf: data.representative_of || null,
            greetingName: data.authenticated_user_name || data.authenticated_first_name || 'User'
        };
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
            console.error('[DEBUG] getInitData: Failed to decode hash data:', e.message);
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
    
    // Log to console with breakdown
    console.error('Mini App Error:', debugInfo);
    console.error('[DEBUG] Telegram WebApp state:', debugInfo.telegramWebApp);
    console.error('[DEBUG] Network state:', debugInfo.network);
    
    // Clear and render
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
}

/**
 * Copy debug info to clipboard
 */
function copyDebugInfo() {
    if (!window.currentDebugInfo) {
        alert('No debug info available');
        return;
    }
    
    navigator.clipboard.writeText(window.currentDebugInfo).then(() => {
        alert('Debug info copied to clipboard');
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy debug info');
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
        maximumFractionDigits: 2
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
            console.error('[DEBUG loadTransactions] No init data available from getInitData()');
            return;
        }

        const isRepresenting = (typeof contextOrFlag === 'object') ? !!contextOrFlag.isRepresenting : !!contextOrFlag;
        // Fetch transactions from backend with scope parameter and representing flag
        const url = `/api/mini-app/transactions-list?scope=${scope}&representing=${isRepresenting}`;
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            console.error('[DEBUG loadTransactions] Failed to load transactions:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('[DEBUG loadTransactions] Error response:', errorText);
            return;
        }
        
        const data = await response.json();
        
        // Render transactions
        if (data.transactions && Array.isArray(data.transactions)) {
            renderTransactionsList(data.transactions, containerId);
        }
        
    } catch (error) {
        console.error('[DEBUG loadTransactions] Exception:', error);
        console.error('[DEBUG loadTransactions] Error message:', error.message);
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
        container.innerHTML = '<div class="transaction-empty">No transactions yet</div>';
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
        accountEl.textContent = `${transaction.from_ac_name} → ${transaction.to_ac_name}`;
        
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
 * Load and render electricity bills from backend
 * @param {string} containerId - ID of container to render bills into
 * @param {boolean} isRepresenting - Whether the authenticated user is representing someone else
 */
async function loadBills(containerId = 'bills-list', contextOrFlag = false) {
    try {
        const initData = getInitData();
        
        if (!initData) {
            console.error('[DEBUG loadBills] No init data available from getInitData()');
            return;
        }

        const isRepresenting = (typeof contextOrFlag === 'object') ? !!contextOrFlag.isRepresenting : !!contextOrFlag;
        // Fetch bills from backend with representing flag
        const url = `/api/mini-app/bills?representing=${isRepresenting}`;
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            console.error('[DEBUG loadBills] Failed to load bills:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('[DEBUG loadBills] Error response:', errorText);
            return;
        }
        
        const data = await response.json();
        
        // Debug: Log the response data
        console.log('[bills DEBUG] Full response:', data);
        if (data.bills && data.bills.length > 0) {
            console.log('[bills DEBUG] First bill:', data.bills[0]);
            for (let i = 0; i < Math.min(3, data.bills.length); i++) {
                const bill = data.bills[i];
                console.log(
                    `[bills DEBUG] Bill ${i}: type=${bill.bill_type}, ` +
                    `start_reading=${bill.start_reading}, end_reading=${bill.end_reading}, consumption=${bill.consumption}`
                );
            }
        }
        
        // Render bills
        if (data.bills && Array.isArray(data.bills)) {
            renderBills(data.bills, containerId);
        }
        
    } catch (error) {
        console.error('[DEBUG loadBills] Exception:', error);
        console.error('[DEBUG loadBills] Error message:', error.message);
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
        container.innerHTML = '<div class="bill-empty">No bills yet</div>';
        return;
    }
    
    bills.forEach(bill => {
        const billItem = document.createElement('div');
        billItem.className = 'bill-item';
        
        // Debug: Log bill rendering
        console.log(
            `[renderBills DEBUG] Rendering bill: type=${bill.bill_type}, ` +
            `start_reading=${bill.start_reading}, end_reading=${bill.end_reading}, consumption=${bill.consumption}`
        );
        
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
        'ELECTRICITY': '⚡ Electricity',
        'SHARED_ELECTRICITY': '🔌 Shared Electricity',
        'CONSERVATION': '🏘️ Conservation',
        'MAIN': '📋 Main'
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
            console.error('[DEBUG loadUserStatus] No init data available from getInitData()');
            return;
        }

        // Fetch user status from backend
        const response = await fetchWithTmaAuth('/api/mini-app/user-status', initData);
        
        if (!response.ok) {
            console.error('[DEBUG loadUserStatus] Failed to load user status:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('[DEBUG loadUserStatus] Error response:', errorText);
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
            const initData = getInitData();
            if (!initData) {
                tg.showAlert('Unable to verify Telegram WebApp data');
                return;
            }
            
            // Fetch photo gallery URL from backend config
            const response = await fetchWithTmaAuth('/api/mini-app/config', initData);
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
 * Navigate to transactions page
 */
function navigateToTransactions(event) {
    event.preventDefault();
    
    // Show transactions page
    const template = document.getElementById('transactions-template');
    if (!template) {
        console.error('Transactions template not found');
        return;
    }
    
    const content = template.content.cloneNode(true);
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    
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
            console.error('[DEBUG loadBalance] No init data available from getInitData()');
            return;
        }

        const isRepresenting = (typeof contextOrFlag === 'object') ? !!contextOrFlag.isRepresenting : !!contextOrFlag;
        // Fetch balance from backend with representing flag
        const url = `/api/mini-app/balance?representing=${isRepresenting}`;
        const response = await fetchWithTmaAuth(url, initData);

        if (!response.ok) {
            console.error('[DEBUG loadBalance] Failed to load balance:', response.status, response.statusText);
            return;
        }
        
        const data = await response.json();
        
        if (data.balance !== undefined) {
            renderBalance(data.balance);
        }
        
    } catch (error) {
        console.error('[DEBUG loadBalance] Exception:', error);
    }
}

/**
 * Render balance into the balance-container
 * @param {number} balance - Balance amount (transactions - bills)
 */
function renderBalance(balance) {
    const container = document.getElementById('balance-container');
    
    if (!container) {
        console.warn('Balance container not found');
        return;
    }
    
    // Show the balance section
    container.classList.add('visible');
    
    // Find the balance-value element and update it
    const balanceValue = container.querySelector('.balance-value');
    if (balanceValue) {
        const formattedBalance = formatAmount(Math.abs(balance));
        const balanceClass = balance >= 0 ? 'positive' : 'negative';
        balanceValue.className = `balance-value ${balanceClass}`;
        balanceValue.textContent = `${balance >= 0 ? '+' : '-'}₽${formattedBalance}`;
    }
}

/**
 * Navigate to balances page
 */
function navigateToBalances(event) {
    console.log('[DEBUG navigateToBalances] STARTED');
    event.preventDefault();
    
    // Show balances page
    const template = document.getElementById('balances-template');
    if (!template) {
        console.error('[DEBUG navigateToBalances] balances-template not found');
        return;
    }
    console.log('[DEBUG navigateToBalances] Template found, cloning content');
    
    const content = template.content.cloneNode(true);
    appContainer.innerHTML = '';
    appContainer.appendChild(content);
    console.log('[DEBUG navigateToBalances] Template rendered in DOM');
    
    // Load all balances
    console.log('[DEBUG navigateToBalances] Calling loadBalances');
    loadBalances('balances-list');
    console.log('[DEBUG navigateToBalances] COMPLETED');
}

/**
 * Load and render balances from backend
 * @param {string} containerId - ID of container to render balances into
 */
function loadBalances(containerId = 'balances-list') {
    console.log('[DEBUG loadBalances] STARTED with containerId:', containerId);
    try {
        const initData = getInitData();
        console.log('[DEBUG loadBalances] Got init data:', initData ? 'YES' : 'NO');
        
        if (!initData) {
            console.error('[DEBUG loadBalances] No init data available from getInitData()');
            return;
        }

        // Fetch balances from backend (all users, info available to any owner)
        const url = `/api/mini-app/balances`;
        console.log('[DEBUG loadBalances] Fetching from URL:', url);
        
        fetchWithTmaAuth(url, initData)
            .then(response => {
                console.log('[DEBUG loadBalances] Response status:', response.status);
                
                if (!response.ok) {
                    console.error('[DEBUG loadBalances] Failed to load balances:', response.status, response.statusText);
                    return response.text().then(errorText => {
                        console.error('[DEBUG loadBalances] Error response body:', errorText);
                        throw new Error(`HTTP ${response.status}`);
                    });
                }
                
                return response.json();
            })
            .then(data => {
                console.log('[DEBUG loadBalances] Got data:', data);
                console.log('[DEBUG loadBalances] Balances count:', data.balances ? data.balances.length : 0);
                if (data.balances && data.balances.length > 0) {
                    console.log('[DEBUG loadBalances] First balance:', data.balances[0]);
                }
                console.log('[DEBUG loadBalances] Calling renderBalancesPage with', data.balances ? data.balances.length : 0, 'items');
                renderBalancesPage(data.balances || [], containerId);
                console.log('[DEBUG loadBalances] COMPLETED');
            })
            .catch(error => {
                console.error('[DEBUG loadBalances] Exception:', error);
                console.error('[DEBUG loadBalances] Error message:', error.message);
                console.error('[DEBUG loadBalances] Stack:', error.stack);
            });
        
    } catch (error) {
        console.error('[DEBUG loadBalances] Sync error:', error);
    }
}

/**
 * Render balances page with list of owners and their balances
 * @param {Array} balances - Array of balance items {owner_name, balance, share_percentage}
 * @param {string} containerId - ID of container to render into
 */
function renderBalancesPage(balances, containerId = 'balances-list') {
    console.log('[DEBUG renderBalancesPage] STARTED with', balances.length, 'balances, containerId:', containerId);
    const container = document.getElementById(containerId);
    console.log('[DEBUG renderBalancesPage] Got container:', container ? 'YES' : 'NO');
    
    if (!container) {
        console.warn('[DEBUG renderBalancesPage] balances-list container not found');
        return;
    }
    
    container.innerHTML = '';
    
    if (!balances || balances.length === 0) {
        container.innerHTML = '<div class="balance-empty">No balances available</div>';
        console.log('[DEBUG renderBalancesPage] No balances to render');
        return;
    }
    
    // Sort by balance (most negative first - biggest debt first)
    const sorted = [...balances].sort((a, b) => a.balance - b.balance);
    console.log('[DEBUG renderBalancesPage] Sorted balances:', sorted);
    
    sorted.forEach((item, index) => {
        console.log(`[DEBUG renderBalancesPage] Rendering balance ${index}:`, item);
        const row = document.createElement('div');
        row.className = 'balance-row';
        
        // Owner info (name + share percentage)
        const infoDiv = document.createElement('div');
        infoDiv.className = 'balance-row-info';
        
        const nameEl = document.createElement('div');
        nameEl.className = 'balance-row-name';
        nameEl.textContent = item.owner_name;
        infoDiv.appendChild(nameEl);
        
        if (item.share_percentage !== null) {
            const shareEl = document.createElement('div');
            shareEl.className = 'balance-row-share';
            shareEl.textContent = `${formatAmount(item.share_percentage)}%`;
            infoDiv.appendChild(shareEl);
        }
        
        row.appendChild(infoDiv);
        
        // Balance amount (with color coding)
        const amountEl = document.createElement('div');
        const formattedAmount = formatAmount(Math.abs(item.balance));
        const balanceClass = item.balance >= 0 ? 'positive' : 'negative';
        amountEl.className = `balance-row-amount ${balanceClass}`;
        amountEl.textContent = `${item.balance >= 0 ? '+' : '-'}₽${formattedAmount}`;
        
        row.appendChild(amountEl);
        container.appendChild(row);
        console.log(`[DEBUG renderBalancesPage] Appended balance row ${index}`);
    });
    console.log('[DEBUG renderBalancesPage] COMPLETED - rendered', sorted.length, 'balances');
}

async function initMiniApp() {
    try {
        // Get init data from Telegram WebApp (supports both desktop and iOS)
        const initData = getInitData();
        
        if (!initData) {
            console.error('[DEBUG] initData is missing or empty after getInitData()');
            renderError('Could not verify Telegram authentication. Please open this app from Telegram.');
            return;
        }
        
        try {
            // Call backend API to check registration status
            const response = await fetchWithTmaAuth('/api/mini-app/init', initData);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[DEBUG] API error response:', errorText);
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
                // Unified context approach
                const context = await getAppContext();
                if (context) {
                    renderUserStatuses(context.roles);
                    renderRepresentativeInfo(context.representativeOf);
                    renderStakeholderLink(context.stakeholderUrl, context.isOwner, context.sharePercentage);
                    if (context.isOwner) {
                        await loadProperties(context);
                        await loadBalance(context);
                    }
                    await loadTransactions('transactions-list', 'personal', context);
                    await loadBills('bills-list', context);
                } else {
                    console.error('[init] Failed to establish app context');
                }
            } else {
                renderAccessDenied(data);
            }
            
        } catch (fetchError) {
            console.error('[DEBUG] Fetch error:', fetchError?.message || fetchError);
            throw fetchError; // Re-throw to outer catch
        }
        
    } catch (error) {
        console.error('[DEBUG] Exception in initMiniApp:', error);
        console.error('[DEBUG] Error message:', error.message);
        console.error('[DEBUG] Error stack:', error.stack);
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
        // Fetch properties from backend with representing flag
        const url = `/api/mini-app/properties?representing=${isRepresenting}`;
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
