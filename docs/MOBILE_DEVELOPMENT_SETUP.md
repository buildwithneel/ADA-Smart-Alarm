# ADA Mobile Development Setup Guide
## Cross-Platform React Native (Expo) & Native Android Development

---

## 1. Prerequisites & Environment Setup

### Required Tooling:
- **Node.js**: v20+ or v24+ (verified current environment: Node v24.4.1, npm 11.4.2)
- **Java Development Kit**: JDK 17 (verified current environment: Java 17 toolchain)
- **Android SDK & Tools**: SDK 36, Build-Tools 36.0.0, Platform-Tools (installed at `C:\Users\NEEL\AppData\Local\Android\Sdk`)
- **Python**: 3.10+ (for FastAPI backend)
- **Git**: Installed and configured

### macOS & Xcode Prerequisites (for iOS Development & Builds):
- macOS Sonoma (14+) or Sequoia (15+)
- Xcode 15 or 16 with Command Line Tools (`xcode-select --install`)
- CocoaPods (`brew install cocoapods` or gem)
- Active Apple Developer Account (for device provisioning, capabilities, and TestFlight distribution)
- *Note*: Windows can develop shared TypeScript code, tests, and Expo JavaScript layers, but native iOS builds, signing, simulator execution, and physical iPhone deployment require access to macOS and Xcode.

---

## 2. Directory & Application Identities

| Application | Path | Identifier (Android / iOS) | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Native Android** (Preserved) | `android/` | `com.thinkx.ada` | Kotlin, Jetpack Compose, Room |
| **Cross-Platform Mobile** | `apps/mobile/` | `com.thinkx.ada.mobile` | React Native, TypeScript, Expo Dev Client |
| **Shared Core Library** | `packages/shared/` | `@ada/shared` | Pure TypeScript (Isomorphic) |
| **FastAPI Backend** | `backend/` | N/A | Python 3.10, FastAPI, PostgreSQL, Redis |
| **Web Dashboard** | `frontend/` | N/A | React 19, Vite, Tailwind CSS |

---

## 3. Environment Variables Configuration

Create `.env` in `apps/mobile/` (derived from `.env.example`):

```bash
# API Base URL configuration
# For Android Emulator:
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000/api/v1

# For iOS Simulator on macOS:
# EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1

# For Physical Phone testing on local Wi-Fi:
# EXPO_PUBLIC_API_URL=http://192.168.1.100:8000/api/v1

# For Production:
# EXPO_PUBLIC_API_URL=https://api.ada-alarm.app/api/v1

# Firebase Client Configuration (Mobile)
EXPO_PUBLIC_FIREBASE_API_KEY=AIzaSyDummyKeyForDevelopmentPreview
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=ada-dynamic-alarm.firebaseapp.com
EXPO_PUBLIC_FIREBASE_PROJECT_ID=ada-dynamic-alarm
EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET=ada-dynamic-alarm.appspot.com
EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789012
EXPO_PUBLIC_FIREBASE_APP_ID=1:123456789012:ios:abcdef1234567890
```

---

## 4. Running Backend Services

From repository root:
```powershell
# Start PostgreSQL & Redis via Docker
docker-compose up -d postgres redis

# Run FastAPI backend locally
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 5. Working on the Preserved Native Android App

From repository root:
```powershell
cd android

# Run unit tests
.\gradlew.bat testDebugUnitTest

# Build debug APK (installed to physical device or emulator)
.\gradlew.bat assembleDebug

# Install to connected device via ADB
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

---

## 6. Developing the Cross-Platform Mobile App (`apps/mobile`)

From `apps/mobile/`:
```bash
# Install dependencies
npm install

# Run TypeScript check
npm run typecheck

# Run unit tests
npm test

# Start Expo dev server
npx expo start

# Run on iOS Simulator (macOS only)
npx expo run:ios

# Run on Android Emulator with distinct package ID (com.thinkx.ada.mobile)
npx expo run:android
```
