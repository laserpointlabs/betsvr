// Configuration - LLM provider base URL (lmsvr)
// Chat/models/auth are served by lmsvr ("lmapi").
const API_BASE_URL = window.location.hostname === 'bet.laserpointlabs.com'
    ? 'https://lmapi.laserpointlabs.com'
    : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? 'http://localhost:8001'
        : 'https://lmapi.laserpointlabs.com';

// Betting alerts are served by betsvr (same-origin), and proxied by nginx -> bet_api.
// This keeps alerts traffic on bet.* and avoids CORS issues.
const ALERTS_BASE_URL = '';

// Get default model from environment variable (set via Docker env)
// Default to a local/provider-independent model so the UI works even if OpenAI isn't configured.
const DEFAULT_MODEL = window.DEFAULT_MODEL || 'granite4:3b';

// Allowed models - exact matches only
// Note: gpt-4o is the premium model with best reasoning
const ALLOWED_MODELS = ['gpt-4o', 'granite4:3b', 'qwen2.5:32b'];

// State
let apiKey = localStorage.getItem('api_key');
let deviceToken = localStorage.getItem('device_token');
let conversationHistory = JSON.parse(localStorage.getItem('conversation_history') || '[]');
let currentModel = localStorage.getItem('current_model') || DEFAULT_MODEL;

// DOM Elements
const apiKeyInput = document.getElementById('api-key-input');
const saveKeyBtn = document.getElementById('save-key-btn');
const keyStatus = document.getElementById('key-status');
const chatSection = document.getElementById('chat-section');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const modelSelect = document.getElementById('model-select');
const errorMessage = document.getElementById('error-message');
const toggleSettingsBtn = document.getElementById('toggle-settings-btn');
const settingsPanel = document.getElementById('settings-panel');
const alertsBtn = document.getElementById('alerts-btn');
const alertsPanel = document.getElementById('alerts-panel');
const alertsList = document.getElementById('alerts-list');
const alertBadge = document.getElementById('alert-badge');
const refreshAlertsBtn = document.getElementById('refresh-alerts-btn');

// Alerts state
let lastAlertCount = 0;
let alertsPollingInterval = null;
let seenAlertIds = new Set(JSON.parse(localStorage.getItem('seen_alerts') || '[]'));

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check for API key in URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const keyFromUrl = urlParams.get('key');

    if (keyFromUrl) {
        // Key provided in URL - auto-fill the input field
        apiKeyInput.value = keyFromUrl;
        apiKeyInput.type = 'text'; // Show the key so user can see it
        // Clean URL (remove key parameter for security)
        window.history.replaceState({}, document.title, window.location.pathname);
        // Show message to save the key
        keyStatus.textContent = 'Click "Save Key" to activate';
        keyStatus.className = 'key-status';
    } else if (deviceToken) {
        // Device token exists - verify it with server
        const verified = await verifyDeviceToken();
        if (verified) {
            showChatInterface();
            loadModels();
        } else {
            // Token invalid, clear it and show key input
            localStorage.removeItem('device_token');
            deviceToken = null;
            showApiKeyInput();
        }
    } else if (apiKey) {
        // Legacy: API key in localStorage but no device token
        // Try to register the device
        const registered = await registerDevice(apiKey);
        if (registered) {
            showChatInterface();
            loadModels();
        } else {
            showApiKeyInput();
        }
    } else {
        showApiKeyInput();
    }

    // Device manager is initialized in device-manager.js
    setTimeout(() => {
        if (typeof deviceManager !== 'undefined') {
            deviceManager.updateDeviceInfo();
        }
    }, 100);

    // Event listeners
    saveKeyBtn.addEventListener('click', saveApiKey);
    apiKeyInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') saveApiKey();
    });
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    modelSelect.addEventListener('change', (e) => {
        currentModel = e.target.value;
        localStorage.setItem('current_model', currentModel);
    });

    // Clear chat button
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', clearConversation);
    }

    // Settings toggle
    if (toggleSettingsBtn) {
        toggleSettingsBtn.addEventListener('click', toggleSettings);
    }
});

// Toggle settings panel visibility
function toggleSettings() {
    if (settingsPanel.classList.contains('collapsed')) {
        settingsPanel.classList.remove('collapsed');
    } else {
        settingsPanel.classList.add('collapsed');
    }
}

// Verify device token with server
async function verifyDeviceToken() {
    if (!deviceToken) return false;

    try {
        const response = await fetch(`${API_BASE_URL}/api/verify-device`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ device_token: deviceToken })
        });

        if (!response.ok) return false;

        const data = await response.json();
        if (data.valid) {
            keyStatus.textContent = `✓ Welcome back, ${data.customer_name}`;
            keyStatus.className = 'key-status valid';
            return true;
        }
        return false;
    } catch (error) {
        console.error('Error verifying device:', error);
        return false;
    }
}

// Register device with API key
async function registerDevice(key) {
    try {
        // Get device info
        let deviceName = 'Unknown Device';
        let deviceType = 'computer';

        if (typeof deviceManager !== 'undefined') {
            deviceName = deviceManager.getDeviceName();
            deviceType = deviceManager.getDeviceType();
        }

        const response = await fetch(`${API_BASE_URL}/api/register-device`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: key,
                device_name: deviceName,
                device_type: deviceType
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to register device');
        }

        const data = await response.json();
        if (data.success) {
            // Save device token (not the API key!)
            deviceToken = data.device_token;
            localStorage.setItem('device_token', deviceToken);
            // Keep API key temporarily for API calls
            apiKey = key;
            localStorage.setItem('api_key', key);

            keyStatus.textContent = `✓ Device registered for ${data.customer_name}`;
            keyStatus.className = 'key-status valid';
            return true;
        }
        return false;
    } catch (error) {
        console.error('Error registering device:', error);
        keyStatus.textContent = error.message;
        keyStatus.className = 'key-status invalid';
        return false;
    }
}

function showApiKeyInput() {
    chatSection.style.display = 'none';
    if (!keyStatus.textContent) {
        keyStatus.textContent = '';
    }
    // Show settings panel, hide gear button
    if (settingsPanel && toggleSettingsBtn) {
        settingsPanel.classList.remove('collapsed');
        toggleSettingsBtn.style.display = 'none';
    }
}

function showChatInterface() {
    chatSection.style.display = 'flex';
    if (!keyStatus.textContent.includes('✓')) {
        keyStatus.textContent = '✓ Connected';
        keyStatus.className = 'key-status valid';
    }
    // Collapse settings and show gear button
    if (settingsPanel && toggleSettingsBtn) {
        settingsPanel.classList.add('collapsed');
        toggleSettingsBtn.style.display = 'flex';
    }
    // Restore conversation history to UI
    restoreConversation();
}

// Restore conversation from localStorage
function restoreConversation() {
    if (conversationHistory.length > 0) {
        messagesDiv.innerHTML = ''; // Clear any existing messages
        conversationHistory.forEach(msg => {
            addMessage(msg.role === 'user' ? 'user' : 'assistant', msg.content);
        });
        scrollToBottom();
    }
}

// Save conversation to localStorage
function saveConversation() {
    localStorage.setItem('conversation_history', JSON.stringify(conversationHistory));
}

// Clear conversation
function clearConversation() {
    conversationHistory = [];
    localStorage.removeItem('conversation_history');
    messagesDiv.innerHTML = '';
}

async function saveApiKey() {
    const key = apiKeyInput.value.trim();
    if (!key) {
        keyStatus.textContent = 'Please enter an API key';
        keyStatus.className = 'key-status invalid';
        return;
    }

    // Show loading state
    saveKeyBtn.disabled = true;
    saveKeyBtn.textContent = 'Registering...';
    keyStatus.textContent = 'Registering device...';
    keyStatus.className = 'key-status';

    // Register device with the API key
    const registered = await registerDevice(key);

    // Reset button
    saveKeyBtn.disabled = false;
    saveKeyBtn.textContent = 'Save Key';

    if (registered) {
        showChatInterface();
        loadModels();
    }
}

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/models`, {
            headers: {
                'Authorization': `Bearer ${apiKey}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Invalid API key');
            }
            throw new Error('Failed to load models');
        }

        const data = await response.json();
        const allModels = data.models || [];

        // Filter to only allowed models (exact match)
        const models = allModels.filter(model => ALLOWED_MODELS.includes(model.name));

        // Populate model select
        modelSelect.innerHTML = '';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            if (model.name === DEFAULT_MODEL) {
                option.selected = true;
                currentModel = DEFAULT_MODEL;
            }
            modelSelect.appendChild(option);
        });

        if (models.length === 0) {
            modelSelect.innerHTML = '<option value="">No models available</option>';
        }
    } catch (error) {
        showError(`Failed to load models: ${error.message}`);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
    }
}

// Render markdown to HTML
function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        // Configure marked for safe rendering
        marked.setOptions({
            breaks: true,  // Convert \n to <br>
            gfm: true,     // GitHub Flavored Markdown
        });
        return marked.parse(text);
    }
    // Fallback: escape HTML and convert newlines
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = role === 'user' ? 'You' : 'Assistant';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Render markdown for assistant messages, plain text for user
    if (role === 'assistant' && content) {
        contentDiv.innerHTML = renderMarkdown(content);
    } else {
        contentDiv.textContent = content;
    }

    messageDiv.appendChild(label);
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);

    scrollToBottom();

    return contentDiv;
}

// Update message content with markdown rendering
function updateMessageContent(contentDiv, text) {
    if (typeof marked !== 'undefined') {
        contentDiv.innerHTML = renderMarkdown(text);
    } else {
        contentDiv.textContent = text;
    }
    scrollToBottom();
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || !apiKey || !currentModel) {
        return;
    }

    // Disable input
    messageInput.disabled = true;
    sendBtn.disabled = true;
    sendBtn.querySelector('.loading').style.display = 'inline';

    // Add user message to UI
    addMessage('user', message);

    // Add to conversation history
    conversationHistory.push({ role: 'user', content: message });
    saveConversation();

    // Clear input
    messageInput.value = '';

    try {
        // Create assistant message placeholder with thinking indicator
        const assistantContentDiv = addMessage('assistant', '');
        assistantContentDiv.innerHTML = `
            <div class="thinking-indicator">
                <span>Thinking</span>
                <div class="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        // Send request
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: currentModel,
                messages: conversationHistory,
                stream: true
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Invalid API key. Please check your API key.');
            } else if (response.status === 402) {
                throw new Error('Budget exceeded. Please contact support.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.trim() === '') continue;

                try {
                    const json = JSON.parse(line);

                    // Skip messages with tool_calls (internal processing, not for display)
                    if (json.message && json.message.tool_calls) {
                        console.log('Tool call detected (internal):', json.message.tool_calls);
                        continue; // Don't display to user
                    }

                    if (json.message && json.message.content) {
                        fullResponse += json.message.content;
                        // Update with markdown rendering
                        updateMessageContent(assistantContentDiv, fullResponse);
                        // Auto-scroll
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                } catch (e) {
                    // Skip invalid JSON lines
                    console.error('Error parsing line:', e, line);
                }
            }
        }

        // Add assistant response to conversation history
        conversationHistory.push({ role: 'assistant', content: fullResponse });
        saveConversation();

    } catch (error) {
        showError(error.message);
        // Remove the assistant message placeholder if error
        const lastMessage = messagesDiv.lastElementChild;
        if (lastMessage && lastMessage.classList.contains('assistant')) {
            lastMessage.remove();
        }
    } finally {
        // Re-enable input
        messageInput.disabled = false;
        sendBtn.disabled = false;
        sendBtn.querySelector('.loading').style.display = 'none';
        messageInput.focus();
    }
}

// ============================================================================
// ALERTS FUNCTIONALITY
// ============================================================================

// Toggle alerts panel
function toggleAlertsPanel() {
    if (alertsPanel) {
        alertsPanel.classList.toggle('collapsed');
        // Close settings panel if open
        if (!alertsPanel.classList.contains('collapsed') && settingsPanel) {
            settingsPanel.classList.add('collapsed');
        }
        // Mark all alerts as seen when opening
        if (!alertsPanel.classList.contains('collapsed')) {
            markAllAlertsSeen();
        }
    }
}

// Fetch alerts from API
async function fetchAlerts() {
    if (!apiKey && !deviceToken) return;

    try {
        const response = await fetch(`${ALERTS_BASE_URL}/api/alerts?limit=20`, {
            headers: {
                'Authorization': `Bearer ${apiKey || deviceToken}`
            }
        });

        if (!response.ok) {
            console.error('Failed to fetch alerts:', response.status);
            return;
        }

        const data = await response.json();
        const alerts = data.alerts || [];

        // Update badge count (only unseen alerts)
        const unseenAlerts = alerts.filter(a => !seenAlertIds.has(getAlertId(a)));

        // Play sound/vibrate if new alerts arrived
        if (unseenAlerts.length > 0) {
            playNotificationSound();
            vibratePhone();
        }

        updateAlertBadge(unseenAlerts.length);

        // Render alerts
        renderAlerts(alerts);

    } catch (error) {
        console.error('Error fetching alerts:', error);
    }
}

// Generate unique ID for an alert
function getAlertId(alert) {
    return `${alert.game_id || ''}_${alert.type || ''}_${alert.timestamp || ''}`;
}

// Update the badge count
function updateAlertBadge(count) {
    if (alertBadge) {
        if (count > 0) {
            alertBadge.textContent = count > 99 ? '99+' : count;
            alertBadge.style.display = 'flex';
        } else {
            alertBadge.style.display = 'none';
        }
    }
}

// Mark all alerts as seen
function markAllAlertsSeen() {
    // This will be called when user opens the alerts panel
    // We'll mark current alerts as seen
    fetchAlerts().then(() => {
        updateAlertBadge(0);
    });
}

// Render alerts list
function renderAlerts(alerts) {
    if (!alertsList) return;

    if (!alerts || alerts.length === 0) {
        alertsList.innerHTML = '<p class="no-alerts">No alerts yet. Monitoring for line movements...</p>';
        return;
    }

    alertsList.innerHTML = alerts.map(alert => {
        const significance = alert.significance || 'MEDIUM';
        const alertClass = significance === 'CRITICAL' ? 'critical' :
                          significance === 'HIGH' ? 'high' : '';

        // Format timestamp
        let timeStr = '';
        try {
            const dt = new Date(alert.timestamp);
            timeStr = dt.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
            });
        } catch (e) {
            timeStr = alert.timestamp || '';
        }

        const emoji = significance === 'CRITICAL' ? '🚨' :
                     significance === 'HIGH' ? '🔴' : '🟡';

        // Map sport to emoji
        const sportEmojis = {
            "americanfootball_nfl": "🏈",
            "americanfootball_ncaaf": "🏈",
            "basketball_nba": "🏀",
            "basketball_ncaab": "🏀",
            "baseball_mlb": "⚾",
            "icehockey_nhl": "🏒",
            "soccer": "⚽",
            "tennis": "🎾",
            "mma": "🥊",
            "boxing": "🥊",
            "golf": "⛳"
        };
        // Try to get emoji from alert object, then map, then default
        // Note: alert.sport might be 'americanfootball_nfl' or just 'nfl' depending on source
        let sportEmoji = alert.sport_emoji || sportEmojis[alert.sport];

        if (!sportEmoji) {
             // Fallback: try partial match
             if (alert.sport && alert.sport.includes('football')) sportEmoji = "🏈";
             else if (alert.sport && alert.sport.includes('basketball')) sportEmoji = "🏀";
             else if (alert.sport && alert.sport.includes('baseball')) sportEmoji = "⚾";
             else if (alert.sport && alert.sport.includes('hockey')) sportEmoji = "🏒";
             else sportEmoji = '🎮';
        }

        // Create prompt for analysis
        const prompt = `Analyze this line movement: ${sportEmoji} ${alert.game} - ${alert.movement}. Why is this happening? Check news and injuries. Any betting opportunities?`;
        const safePrompt = prompt.replace(/'/g, "&apos;").replace(/"/g, "&quot;");

        return `
            <div class="alert-item ${alertClass}">
                <div class="alert-type">${emoji} ${alert.type || 'Alert'} <span class="sport-emoji">${sportEmoji}</span></div>
                <div class="alert-game">${alert.game || 'Unknown Game'}</div>
                <div class="alert-detail">${alert.movement || ''}</div>
                <div class="alert-time">${timeStr}</div>
                <button class="analyze-btn" onclick="sendAnalysisRequest('${safePrompt}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                    Analyze Movement
                </button>
            </div>
        `;
    }).join('');

    // Save seen alert IDs
    alerts.forEach(a => seenAlertIds.add(getAlertId(a)));
    localStorage.setItem('seen_alerts', JSON.stringify([...seenAlertIds].slice(-200)));
}

// Global function to send analysis request from alert
window.sendAnalysisRequest = function(prompt) {
    if (messageInput && sendBtn) {
        messageInput.value = prompt;
        // Close alerts panel on mobile to show chat
        if (window.innerWidth < 768) {
            toggleAlertsPanel();
        }
        sendMessage();
    }
};

// Trigger manual alert check
async function triggerAlertCheck() {
    if (!apiKey && !deviceToken) return;

    if (refreshAlertsBtn) {
        refreshAlertsBtn.disabled = true;
        refreshAlertsBtn.style.opacity = '0.5';
    }

    try {
        const response = await fetch(`${ALERTS_BASE_URL}/api/alerts/check`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey || deviceToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Refresh alerts after check
            setTimeout(fetchAlerts, 1000);
        }
    } catch (error) {
        console.error('Error triggering alert check:', error);
    } finally {
        if (refreshAlertsBtn) {
            refreshAlertsBtn.disabled = false;
            refreshAlertsBtn.style.opacity = '1';
        }
    }
}

// Start polling for alerts
function startAlertsPolling() {
    // Poll every 15 seconds
    if (alertsPollingInterval) {
        clearInterval(alertsPollingInterval);
    }

    // Initial fetch
    fetchAlerts();

    // Set up polling (poll every 60 seconds to save resources)
    alertsPollingInterval = setInterval(fetchAlerts, 60000);
}

// Stop polling
function stopAlertsPolling() {
    if (alertsPollingInterval) {
        clearInterval(alertsPollingInterval);
        alertsPollingInterval = null;
    }
}

// Audio Context (global)
let audioCtx = null;

// Initialize Audio on first user interaction
function initAudio() {
    if (!audioCtx) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            audioCtx = new AudioContext();
            // Try to resume immediately (if state is suspended)
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
        }
    }
    // Remove listeners once initialized
    document.removeEventListener('click', initAudio);
    document.removeEventListener('touchstart', initAudio);
    document.removeEventListener('keydown', initAudio);
}

// Play notification sound (beep)
function playNotificationSound() {
    try {
        if (!audioCtx) {
            // Try to init if not yet ready (might fail if no user interaction yet)
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                audioCtx = new AudioContext();
            } else {
                return;
            }
        }

        // Ensure context is running
        if (audioCtx.state === 'suspended') {
            audioCtx.resume().catch(e => console.log("Audio resume failed", e));
        }

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
        osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.1); // Drop to A4

        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
    } catch (e) {
        console.error('Audio play error:', e);
    }
}

// Vibrate phone (if supported)
function vibratePhone() {
    if (navigator.vibrate) {
        // Vibrate: 200ms on, 100ms off, 200ms on
        try {
            navigator.vibrate([200, 100, 200]);
        } catch (e) {
            console.log("Vibration failed", e);
        }
    }
}

// Initialize alerts event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Init audio on interaction
    document.addEventListener('click', initAudio);
    document.addEventListener('touchstart', initAudio);
    document.addEventListener('keydown', initAudio);
    // Alerts button click
    if (alertsBtn) {
        alertsBtn.addEventListener('click', toggleAlertsPanel);
    }

    // Refresh alerts button
    if (refreshAlertsBtn) {
        refreshAlertsBtn.addEventListener('click', triggerAlertCheck);
    }

    // Start polling if user is authenticated
    if (apiKey || deviceToken) {
        startAlertsPolling();
    }
});
