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
 * Handle menu item click
 */
function handleMenuAction(action) {
    // Show Telegram alert (placeholder for future implementation)
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
