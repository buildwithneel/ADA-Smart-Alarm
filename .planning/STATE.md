# Project Memory & Current State

## Current Position
- **Active Milestone**: Milestone 6 completed (Firebase Authentication and FastAPI Integration); advancing to Milestone 7 (Verification, Code Review & Release Quality).
- **Verified Deliverables**:
  - Jetpack Compose + Material 3 UI screens implemented:
    - Home Dashboard (`HomeScreen`, `HomeViewModel`): Next Alarm spotlight card with countdown, upcoming alarms list from Room Flow, toggle controls synchronized with `AlarmScheduler`, exact-alarm permission banner, cloud sync action and account shortcut.
    - Create/Edit Alarm (`CreateEditAlarmScreen`, `CreateEditAlarmViewModel`): Destination selection with saved/recent quick chips, arrival date/time pickers, duration sliders, live calculation preview card matching `AdaCalculationEngine`, validation preventing past schedules, asynchronous background sync push with local-first guarantee.
    - Destination Management (`DestinationsScreen`, `DestinationsViewModel`): Saved destinations and recent destinations list, add/edit modal, delete confirmation.
    - Settings (`SettingsScreen`, `SettingsViewModel`): Default preparation, safety buffer, snooze durations, Theme preference (System/Dark/Light), vibration switch, exact alarm and notification permission status & settings shortcuts, Account & Cloud Sync management.
    - Authentication Screen (`AuthScreen`, `AuthViewModel`): Material 3 tabbed interface for Email/Password Sign In, Registration, and Password Reset, Google Sign-In, error/validation banners, and Continue Offline option.
  - Authentication Architecture:
    - Domain `AuthUser` and `AuthState` models.
    - `AuthRepository` interface and `FirebaseAuthRepository` using official Firebase Android SDK with safe fallback.
    - Session restoration across app restarts via `FirebaseAuth.addAuthStateListener`.
  - Secure Android-to-FastAPI Networking:
    - `AdaApiService` Retrofit client matching FastAPI backend contracts (`/users/me`, `/alarms`, `/destinations`).
    - `AuthInterceptor` automatically injecting `Authorization: Bearer <token>` with proactive 401 token refresh retry.
    - Base URL configuration in `BuildConfig` supporting Android emulator (`10.0.2.2:8000`) and production HTTPS.
    - `network_security_config.xml` enforcing HTTPS while permitting development loopback.
  - Offline-First Synchronization Layer:
    - `AlarmSyncRepository` bridging Room and FastAPI backend.
    - Stable mapping between local alarm IDs (Room primary key) and server IDs (`serverId`), using local ID as `X-Idempotency-Key` to prevent duplicate submissions during retries.
    - Conflict resolution ensuring pending local edits are never overwritten by stale remote data.
    - Deletion queue preserving consistency when deleting while offline.
    - Zero dependency on network availability at alarm ring time.
  - 68/68 Android unit tests passing across calculations, scheduler, recovery, state transitions, ViewModels, AuthViewModel, AuthInterceptor, and AlarmSyncRepository.
  - 9/9 Backend tests passing in `test_auth.py` and `test_sync.py` covering token verification, user synchronization, unauthenticated rejection, user isolation, and idempotent retries.
  - `assembleDebug` APK build verified (`app-debug.apk`, 15.7 MB).

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
