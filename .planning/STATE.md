# Project Memory & Current State

## Current Position
- **Active Milestone**: Milestone 7 completed; active on Milestone 8 (Cross-Platform Mobile Expansion: Android Preservation + iOS Support + Shared TypeScript Architecture).
- **Verified Deliverables**:
  - Native Android (`android/`):
    - Jetpack Compose + Material 3 UI screens (`HomeScreen`, `CreateEditAlarmScreen`, `DestinationsScreen`, `SettingsScreen`, `AuthScreen`, `AlarmActivity`).
    - Destination-aware journey tracking: `JourneyTrackingCoordinator`, `JourneyTrackingService`, `JourneyScheduler`, `DynamicEtaEngine.kt`.
    - 97/97 Android unit tests passing (`testDebugUnitTest --rerun-tasks`).
    - `assembleDebug` APK build verified (`app-debug.apk`).
  - Backend (`backend/`):
    - FastAPI proxying Google Maps & Mapbox with live road traffic and Redis caching.
    - Offline Great-Circle heuristic fallback.
    - 131/131 pytest tests passing.
  - Web Frontend (`frontend/`):
    - 29/29 Vitest tests passing.
  - Cross-Platform Mobile Expansion (Milestone A Complete):
    - Architecture blueprint: `docs/CROSS_PLATFORM_ARCHITECTURE.md`.
    - iOS Background tracking: `docs/IOS_BACKGROUND_LOCATION.md`.
    - Setup runbook: `docs/MOBILE_DEVELOPMENT_SETUP.md`.
    - Verification matrix: `docs/MOBILE_TEST_PLAN.md`.
    - iOS release readiness: `docs/IOS_RELEASE_CHECKLIST.md`.

## Decision Log
- **D-01 (Architecture)**: Android app lives in `android/` directory in repository root, keeping backend and web frontend intact.
- **D-02 (SDK Targets)**: Android SDK Platform 36 and Build-Tools 36.0.0 installed; `compileSdk = 36`, `targetSdk = 35` (Android 15), `minSdk = 26` (Android 8.0).
- **D-03 (Alarm Engine)**: Uses `AlarmManager.setAlarmClock()` exclusively for reliable user-facing alarm execution.
- **D-04 (Offline First)**: Room local SQLite database owns the canonical device alarm schedule; backend network failures do not prevent local scheduling.
- **D-05 (Time Representation)**: Stored as canonical epoch milliseconds in UTC (`requiredArrivalEpochMs`, `plannedArrivalEpochMs`, `recommendedLeaveEpochMs`, `recommendedWakeEpochMs`, `scheduledAlarmEpochMs`) to prevent time zone and DST drift.
- **D-06 (Exact Alarm Policy)**: Declares both `SCHEDULE_EXACT_ALARM` (runtime checkable) and `USE_EXACT_ALARM` (permitted by Google Play policy for core alarm clock applications).
- **D-07 (Foreground Service)**: Uses `FOREGROUND_SERVICE_SPECIAL_USE` with `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` declared in manifest for Android 14+ conformance.
- **D-08 (Idempotent Sync)**: Local alarm UUID is submitted as `X-Idempotency-Key` to FastAPI backend; server UUID stored in `AlarmEntity.serverId` with separate `syncStatus` column.
- **D-09 (Network Security)**: `network_security_config.xml` enforces HTTPS by default while permitting cleartext solely for `10.0.2.2` (Android emulator loopback) and `localhost`.
- **D-10 (Cross-Platform Isolation)**: The native Android app (`com.thinkx.ada`) remains completely preserved. The cross-platform mobile app lives in `apps/mobile/` with package ID `com.thinkx.ada.mobile` on Android and bundle ID `com.thinkx.ada.mobile` on iOS to prevent collision.
- **D-11 (Shared Domain Extraction)**: Pure TypeScript math, validation, and API contracts reside in `packages/shared/` to eliminate algorithmic divergence between web and mobile.
- **D-12 (iOS Background Policy)**: iOS uses `UIBackgroundModes: ["location"]` with two-step authorization (WhenInUse -> Always Allow) and continuous `showsBackgroundLocationIndicator` during active journeys; no reliance on invalid background JS timers.
- **D-13 (Credential Security)**: Mobile tokens are stored in hardware-backed secure storage via `expo-secure-store` (iOS Keychain / Android KeyStore); plaintext AsyncStorage for tokens is prohibited.
- **D-14 (Zero Monorepo Disruption)**: Existing `frontend/`, `android/`, and `backend/` directories remain in place to avoid breaking CI pipelines or local workflows.
