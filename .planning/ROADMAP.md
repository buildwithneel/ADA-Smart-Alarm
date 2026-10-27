# ADA Smart Alarm — Implementation Roadmap

## Milestones Overview

### Milestone 1: Workspace Audit, Toolchain & Foundation Verification
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - Android project scaffolded in `/android` with AGP 9.0.1, Kotlin 2.3, compileSdk 36, targetSdk 35, Java 17 toolchain.
  - Gradle wrapper verification and build pipeline baseline (`app-debug.apk` built).
  - `.planning/` artifacts (PROJECT, REQUIREMENTS, ROADMAP, STATE).

### Milestone 2: Domain Engine & Pure Calculation Unit Tests
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - `AdaCalculationEngine.kt`, `CalculationInput.kt`, `CalculationResult.kt`.
  - 8/8 domain calculation unit tests passing in `AdaCalculationEngineTest.kt` (including Charusat 9am arrival canonical test case, overnight/midnight crossings, zero buffers, and validation).

### Milestone 3: Local Persistence Layer (Room + DataStore)
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - `AlarmEntity` with canonical epoch milliseconds time milestones and metadata.
  - `DestinationEntity` for saved and recent destinations.
  - `AlarmDao` and `DestinationDao` with reactive Flow and suspend queries.
  - `AdaDatabase` Room database implementation with KSP code generation.
  - `UserPreferencesRepository` backed by AndroidX DataStore Preferences.
  - `AlarmRepository` and `DestinationRepository` interfaces and Room implementations.

### Milestone 4: Native Android Alarm Engine (AlarmManager, Receivers & Audio)
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - `AlarmScheduler` interface and `AndroidAlarmScheduler` using `AlarmManager.setAlarmClock()`.
  - PendingIntent identity, immutability (`FLAG_UPDATE_CURRENT or FLAG_IMMUTABLE`), and cancellation.
  - Exact alarm permission handling (`canScheduleExactAlarms()` on Android 12+).
  - Permissions declared in `AndroidManifest.xml` (`SCHEDULE_EXACT_ALARM`, `USE_EXACT_ALARM`, `POST_NOTIFICATIONS`, `USE_FULL_SCREEN_INTENT`, `RECEIVE_BOOT_COMPLETED`, `VIBRATE`, `WAKE_LOCK`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE`).
  - `AlarmReceiver` broadcast receiver for alarm execution, dismissal, and snoozing.
  - `BootCompletedReceiver` and `TimeChangeReceiver` for reboot and timezone recovery.
  - `AlarmRecoveryManager` for idempotent alarm re-arming and past alarm expiration.
  - `AlarmPlaybackManager` for looped alarm audio (`AudioAttributes.USAGE_ALARM`), audio focus (`AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE`), and vibration waveform.
  - `AlarmService` foreground ringing service with high-priority notification channel.
  - Full-screen `AlarmActivity` Compose UI with high-contrast Snooze and Dismiss actions.
  - Unit test suites passing: `AlarmSchedulerTest` (6 tests), `AlarmRecoveryManagerTest` (3 tests), `AlarmStateTransitionTest` (3 tests).

### Milestone 5: Jetpack Compose Design System & User-Facing Screens (UI/UX Ultra Pro Max)
- **Goal**: Deliver a polished, modern, calm Material 3 design system and user-facing screens for alarm creation, editing, and listing.
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - Home Dashboard with Next Alarm spotlight, live countdown, toggle switch, and upcoming list from Room.
  - Alarm Creator / Editor with dynamic calculations preview, date & time pickers, prep and safety buffer sliders.
  - Destination search, quick-select chips, and saved destinations list.
  - Settings and Permissions status screen (exact alarm, notifications, theme).
  - 47/47 unit tests passing across calculations, scheduler, recovery, state transitions, and all UI ViewModels.
  - `assembleDebug` APK build verified.


### Milestone 6: Backend Integration, Firebase Authentication & API Sync
- **Goal**: Integrate native Android app with existing FastAPI backend and Firebase Auth.
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - Firebase Authentication Android SDK integration (`FirebaseAuthRepository`, `AuthViewModel`, Material 3 `AuthScreen`) supporting email/password registration, login, password reset, and auth state restoration.
  - Backend Firebase ID token verification using Firebase Admin SDK / JWKS and FastAPI `get_current_user` dependency mapping verified Firebase UID to PostgreSQL `User`.
  - Retrofit HTTP client (`AdaApiService`) with OkHttp `AuthInterceptor` injecting `Authorization: Bearer <token>`, handling silent token refresh and 401 retry, without token logging.
  - Network DTOs matching backend Pydantic schemas (`UserResponse`, `AlarmCreateRequest`, `AlarmResponse`, `AlarmUpdateRequest`, `DestinationRequest`, `DestinationResponse`).
  - Offline-first `AlarmSyncRepository` synchronizing local Room alarms and destinations with backend via `X-Idempotency-Key` deduplication, bidirectional sync, conflict protection (local unpushed edits never overwritten by stale server data), and Room/AlarmManager local ringing independence.
  - 68/68 Android unit tests passing (`AuthViewModelTest`, `AuthInterceptorTest`, `AlarmSyncRepositoryTest`, calculations, scheduler, UI).
  - 9/9 Backend auth and sync tests passing (`test_auth.py`, `test_sync.py`).
  - `assembleDebug` APK build verified (`app-debug.apk`).

### Milestone 7: Destination-Aware Journey Monitoring, Dynamic ETA Engine & Arrival Alerts
- **Goal**: Turn ADA into a reliable, destination-aware journey monitoring and dynamic ETA alert application.
- **Status**: COMPLETE & VERIFIED
- **Deliverables**:
  - Full calculation engine audit documenting mathematical contracts, eliminating fixed wake-up-time assumptions, preventing double-counting of elapsed travel time, and separating live traffic duration from fixed stop buffers.
  - Pure Kotlin `DynamicEtaEngine`, `JourneySchedule`, `JourneyLocationFix`, `DynamicEtaResult`, and `JourneyState` models.
  - Multi-tiered `RoutingProvider` architecture (`BackendRoutingProvider` querying FastAPI/Google Maps/Mapbox, `FallbackRoutingProvider` with offline Great-Circle estimation, and `CompositeRoutingProvider`).
  - Native Android `JourneyScheduler` and `JourneyStartReceiver` scheduling automatic tracking start at configurable lead time (default 15 minutes prior) via `AlarmManager.setAlarmClock()`.
  - Foreground `JourneyTrackingService` (`foregroundServiceType="location"`) targeting 60-second GPS updates, accuracy filtering, GPS jump suppression, persistent notification, and automatic route recalculation upon confirmed route deviation (> 250m).
  - Idempotent proximity alerts: Approaching destination alert (1,000m threshold) and Arrival confirmation (100m threshold with 2-hit confirmation), terminating tracking cleanly on arrival.
  - Modern Jetpack Compose UI with live dynamic ETA, live traffic indicator, remaining distance/duration telemetry, and manual Start/Stop tracking controls.
  - 88/88 Android unit tests passing across calculation engine, state transitions, GPS jump protection, arrival confirmation, scheduler, and UI ViewModels.
  - 29/29 Backend pytest tests passing (`test_auth.py`, `test_sync.py`, `test_location_and_routing.py`).
  - `assembleDebug` APK build verified (`app-debug.apk`).

### Milestone 8: Cross-Platform Mobile Expansion (Android Preservation + iOS Support + Shared TypeScript)
- **Goal**: Expand ADA with an iOS-capable React Native mobile application, extract reusable pure TypeScript calculation and API contracts, while fully preserving the working native Android application.
- **Status**: IN PROGRESS (Milestone A: Architecture & Audit Complete; Milestone B: Foundation In Progress)
- **Deliverables**:
  - Comprehensive Cross-Platform Architecture and Audit (`docs/CROSS_PLATFORM_ARCHITECTURE.md`, `docs/IOS_BACKGROUND_LOCATION.md`, `docs/MOBILE_DEVELOPMENT_SETUP.md`, `docs/MOBILE_TEST_PLAN.md`, `docs/IOS_RELEASE_CHECKLIST.md`).
  - Pure TypeScript shared domain library in `packages/shared/` containing mathematical dynamic ETA engine, journey state machine, distance and polyline algorithms, and typed backend DTOs.
  - Cross-platform React Native + Expo application in `apps/mobile/` with bundle ID `com.thinkx.ada.mobile` (Android & iOS).
  - Native iOS background location capability with accurate `Info.plist` disclosures, two-step authorization, and `showsBackgroundLocationIndicator`.
  - Integration with existing FastAPI backend (`/users/me`, `/destinations`, `/alarms`, `/routes`) using secure credential storage (`expo-secure-store`).
  - Automated unit test suites covering shared domain math, state transitions, mobile view models, and API adapters.
