# QR Code Scanner App

A simple QR code scanner mobile app built with React Native, Expo, and TypeScript that continuously scans QR codes and displays their raw content on screen.

## Features

- Real-time QR code scanning using device camera
- Stops scanning automatically when QR code is detected
- Displays raw decoded content as text (no URL opening or action execution)
- "Kontynuuj" button to clear and resume scanning
- API integration ready (sends scanned data to configurable endpoint)
- Clean, simple UI with camera view and text display area
- Proper camera permission handling for Android and iOS
- TypeScript for type safety

## Tech Stack

- React Native
- Expo SDK 54
- TypeScript
- expo-camera (for QR scanning)

## Prerequisites

- Node.js installed
- pnpm package manager
- Expo Go app on your Android device (for testing)
- Or Android Studio (for building APK)

## Installation

1. Install dependencies:
```bash
pnpm install
```

## Running the App

### Option 1: Using Expo Go (Recommended for Quick Testing)

1. Start the development server:
```bash
pnpm start
```

2. Install Expo Go on your Android device from Google Play Store

3. Scan the QR code shown in the terminal with the Expo Go app

### Option 2: Android Emulator

```bash
pnpm run android
```

### Option 3: Build APK for Android

```bash
# Build development client
pnpm exec eas build --profile development --platform android

# Or build production APK
pnpm exec eas build --profile production --platform android
```

## Usage

1. Launch the app
2. Grant camera permission when prompted
3. Point the camera at a QR code
4. Camera stops scanning automatically and displays the decoded content
5. Scanned data is automatically sent to the configured API endpoint (with 3 second timeout)
6. Click "Kontynuuj" button to clear the text and resume scanning
7. The app displays raw content only - it will NOT open URLs or execute any actions

## API Configuration

To configure the API endpoint when your backend is ready:

1. Open `App.tsx`
2. Update the API configuration constants at the top of the file:
   ```typescript
   const API_ENDPOINT = 'https://your-api.com/verify'; // Your API URL
   const API_METHOD = 'POST'; // HTTP method (GET, POST, PUT, etc.)
   const API_TIMEOUT_MS = 3000; // Timeout in milliseconds
   ```

The app will automatically send POST requests with this JSON body:
```json
{
  "qrData": "scanned_qr_code_content"
}
```

API responses and errors are logged to the console. Update the `sendToApi` function in `App.tsx` to handle responses as needed.

## Safety Features

- Content is displayed as plain text regardless of format (URL, JSON, plain text)
- No automatic link opening or action execution
- Scanned content can be selected and copied manually by the user

## Project Structure

```
mobile-app/
├── App.tsx                 # Main app component with QR scanner
├── app.json               # Expo configuration with camera permissions
├── package.json           # Dependencies
└── tsconfig.json          # TypeScript configuration
```

## Permissions

### Android
- `android.permission.CAMERA` - Required for QR code scanning
- `android.permission.INTERNET` - Required for API calls

### iOS
- `NSCameraUsageDescription` - Required for camera access

## Testing

Test the scanner with various QR code types:
- URLs (e.g., https://example.com)
- Plain text
- JSON data
- Numbers

All content types should be displayed as plain text without any automatic actions.
