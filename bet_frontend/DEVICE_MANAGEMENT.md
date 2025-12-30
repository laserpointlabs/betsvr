# Device Access Management

The Bet Assistant web page now includes device access management to track and manage which computers and phones are accessing the service.

## Features

### Device Detection
- **Automatic Detection**: Detects device type (computer, phone, tablet)
- **Device Fingerprinting**: Creates unique fingerprint for each device
- **Platform Detection**: Identifies platform (Windows, Mac, Linux, Android, iOS)
- **Screen Size Tracking**: Records screen resolution

### Device Management
- **Device Registration**: Automatically registers devices on first access
- **Device List**: View all registered devices
- **Current Device Indicator**: Shows which device you're currently using
- **Device Removal**: Remove access for other devices (cannot remove current device)
- **Last Seen Tracking**: Shows when each device was last active

### User Interface
- **Device Info Display**: Shows current device in header
- **Manage Devices Button**: Opens device management modal
- **Device Management Modal**: Full interface for viewing and managing devices
- **Device Icons**: Visual indicators (💻 computer, 📱 phone/tablet)

## How It Works

### Device Fingerprinting
Each device is identified using a combination of:
- User Agent string
- Screen resolution
- Timezone
- Hardware concurrency
- Device memory
- Canvas fingerprinting

This creates a unique identifier that persists across sessions.

### Storage
- Device information is stored in browser `localStorage`
- Each device maintains its own list of registered devices
- Device data includes:
  - Device ID (fingerprint)
  - Device name (e.g., "Windows Computer", "iOS Phone")
  - Device type (computer/phone/tablet)
  - Platform (Windows/Mac/Linux/Android/iOS)
  - Screen size
  - Registration date
  - Last seen timestamp

## Usage

### Viewing Current Device
The current device is automatically displayed in the header after you enter your API key:
```
💻 Windows Computer  [Manage Devices]
```

### Managing Devices
1. Click "Manage Devices" button in the header
2. View all registered devices in the modal
3. See device details:
   - Device type and platform
   - Screen resolution
   - Registration date
   - Last seen timestamp
4. Remove devices (except current device)

### Removing Device Access
1. Open device management modal
2. Click "Remove" button on any device (except current)
3. Confirm removal
4. Device will be removed from the list

**Note**: You cannot remove the current device you're using. This prevents accidentally locking yourself out.

## Device Types

### Computer
- Desktop and laptop computers
- Icon: 💻
- Detected when: Not mobile/tablet user agent

### Phone
- Mobile phones (Android, iPhone)
- Icon: 📱
- Detected when: Mobile user agent detected

### Tablet
- Tablets (iPad, Android tablets)
- Icon: 📱
- Detected when: Tablet user agent detected

## Technical Details

### Files
- `device-manager.js` - Device detection and management logic
- `style.css` - Device management UI styles
- `index.html` - Device management UI elements

### Browser Compatibility
- Works in all modern browsers
- Requires localStorage support
- Requires Canvas API for fingerprinting

### Privacy
- All device data is stored locally in your browser
- No device information is sent to the server
- Device fingerprinting is done client-side only
- You can clear device data by clearing browser localStorage

## Future Enhancements

Potential future features:
- Server-side device tracking (requires API changes)
- Device access limits (max devices per account)
- Device access expiration
- Device access notifications
- Remote device logout
- Device access history/audit log


