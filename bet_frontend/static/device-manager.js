// Device Manager - Handles device detection, fingerprinting, and management

class DeviceManager {
    constructor() {
        this.currentDeviceId = null;
        this.devices = this.loadDevices();
        this.init();
    }

    init() {
        // Detect and register current device
        this.currentDeviceId = this.getDeviceFingerprint();
        this.registerCurrentDevice();
        this.updateDeviceInfo();
    }

    // Generate device fingerprint
    getDeviceFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Device fingerprint', 2, 2);

        const fingerprint = [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height,
            new Date().getTimezoneOffset(),
            canvas.toDataURL(),
            navigator.hardwareConcurrency || 'unknown',
            navigator.deviceMemory || 'unknown'
        ].join('|');

        // Simple hash
        let hash = 0;
        for (let i = 0; i < fingerprint.length; i++) {
            const char = fingerprint.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }

        return Math.abs(hash).toString(36);
    }

    // Detect device type
    getDeviceType() {
        const ua = navigator.userAgent.toLowerCase();
        const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(ua);
        const isTablet = /ipad|android(?!.*mobile)|tablet/i.test(ua);

        if (isTablet) return 'tablet';
        if (isMobile) return 'phone';
        return 'computer';
    }

    // Get device name
    getDeviceName() {
        const type = this.getDeviceType();
        const platform = this.getPlatform();
        return `${platform} ${type.charAt(0).toUpperCase() + type.slice(1)}`;
    }

    // Get platform name
    getPlatform() {
        const ua = navigator.userAgent;
        if (ua.includes('Windows')) return 'Windows';
        if (ua.includes('Mac')) return 'Mac';
        if (ua.includes('Linux')) return 'Linux';
        if (ua.includes('Android')) return 'Android';
        if (ua.includes('iOS') || ua.includes('iPhone') || ua.includes('iPad')) return 'iOS';
        return 'Unknown';
    }

    // Register current device
    registerCurrentDevice() {
        const deviceInfo = {
            id: this.currentDeviceId,
            name: this.getDeviceName(),
            type: this.getDeviceType(),
            platform: this.getPlatform(),
            userAgent: navigator.userAgent,
            screenSize: `${screen.width}x${screen.height}`,
            registeredAt: new Date().toISOString(),
            lastSeen: new Date().toISOString(),
            isCurrent: true
        };

        // Check if device already exists
        const existingIndex = this.devices.findIndex(d => d.id === this.currentDeviceId);
        if (existingIndex >= 0) {
            // Update last seen
            this.devices[existingIndex].lastSeen = new Date().toISOString();
            this.devices[existingIndex].isCurrent = true;
        } else {
            // Add new device
            this.devices.push(deviceInfo);
        }

        // Mark other devices as not current
        this.devices.forEach(d => {
            if (d.id !== this.currentDeviceId) {
                d.isCurrent = false;
            }
        });

        this.saveDevices();
    }

    // Load devices from localStorage
    loadDevices() {
        try {
            const stored = localStorage.getItem('registered_devices');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.error('Error loading devices:', e);
            return [];
        }
    }

    // Save devices to localStorage
    saveDevices() {
        try {
            localStorage.setItem('registered_devices', JSON.stringify(this.devices));
        } catch (e) {
            console.error('Error saving devices:', e);
        }
    }

    // Update device info display
    updateDeviceInfo() {
        const deviceInfo = document.getElementById('device-info');

        // Only show manage devices button if we have devices and element exists
        if (deviceInfo && this.devices.length > 0) {
            deviceInfo.style.display = 'flex';
        }
    }

    // Get device icon
    getDeviceIcon(type) {
        // Return empty string - no icon needed
        return '';
    }

    // Get all devices
    getAllDevices() {
        return this.devices;
    }

    // Remove device
    removeDevice(deviceId) {
        this.devices = this.devices.filter(d => d.id !== deviceId);
        this.saveDevices();
        return true;
    }

    // Get current device info
    getCurrentDevice() {
        return this.devices.find(d => d.id === this.currentDeviceId) || null;
    }

    // Format date
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
}

// Initialize device manager
const deviceManager = new DeviceManager();

// Device Management UI
function showDeviceManagement() {
    const modal = document.getElementById('device-modal');
    const deviceList = document.getElementById('device-list');

    const devices = deviceManager.getAllDevices();

    if (devices.length === 0) {
        deviceList.innerHTML = '<p class="no-devices">No devices registered yet.</p>';
    } else {
        deviceList.innerHTML = devices.map(device => {
            const isCurrent = device.id === deviceManager.currentDeviceId;
            const lastSeen = deviceManager.formatDate(device.lastSeen);
            const registered = deviceManager.formatDate(device.registeredAt);

            return `
                <div class="device-item ${isCurrent ? 'current-device' : ''}">
                    <div class="device-details">
                        <div class="device-name">
                            ${device.type.charAt(0).toUpperCase() + device.type.slice(1)} - ${device.platform}
                            ${isCurrent ? '<span class="current-badge">Current</span>' : ''}
                        </div>
                        <div class="device-info-text">
                            <div>Type: ${device.type}</div>
                            <div>Platform: ${device.platform}</div>
                            <div>Screen: ${device.screenSize}</div>
                            <div>Registered: ${registered}</div>
                            <div>Last seen: ${lastSeen}</div>
                        </div>
                    </div>
                    <div class="device-actions">
                        ${!isCurrent ? `<button class="btn-remove" onclick="removeDevice('${device.id}')">Remove</button>` : '<span class="cannot-remove">Cannot remove current device</span>'}
                    </div>
                </div>
            `;
        }).join('');
    }

    modal.style.display = 'flex';
}

function hideDeviceManagement() {
    const modal = document.getElementById('device-modal');
    modal.style.display = 'none';
}

function removeDevice(deviceId) {
    if (confirm('Are you sure you want to remove this device? You will need to re-register it to access from this device again.')) {
        deviceManager.removeDevice(deviceId);
        showDeviceManagement(); // Refresh the list
    }
}

// Event listeners for device management
document.addEventListener('DOMContentLoaded', () => {
    const manageDevicesBtn = document.getElementById('manage-devices-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const closeModalBtn2 = document.getElementById('close-modal-btn-2');
    const refreshDevicesBtn = document.getElementById('refresh-devices-btn');

    if (manageDevicesBtn) {
        manageDevicesBtn.addEventListener('click', showDeviceManagement);
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', hideDeviceManagement);
    }

    if (closeModalBtn2) {
        closeModalBtn2.addEventListener('click', hideDeviceManagement);
    }

    if (refreshDevicesBtn) {
        refreshDevicesBtn.addEventListener('click', () => {
            deviceManager.registerCurrentDevice();
            showDeviceManagement();
        });
    }

    // Close modal when clicking outside
    const modal = document.getElementById('device-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideDeviceManagement();
            }
        });
    }
});
