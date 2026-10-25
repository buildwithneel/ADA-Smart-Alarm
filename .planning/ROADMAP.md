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
- **Status**: PENDING
- **Deliverables**:
  - Retrofit HTTP client with Bearer token authenticator.
  - DTOs matching backend Pydantic schemas.
  - Sync repository that syncs local Room alarms with backend without blocking local creation.
  - Geocoding and route calculation backend integration.

### Milestone 7: Verification, Code Review & Release Quality
- **Goal**: End-to-end integration testing, code review, linting, and final verification report.
- **Status**: PENDING
- **Deliverables**:
  - Automated tests passing.
  - Verification checklist for lock screen, backgrounding, reboot, offline delivery.
  - Complete documentation and build summary.
