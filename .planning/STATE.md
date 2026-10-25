# Project Memory & Current State

## Current Position
- **Active Milestone**: Milestone 4 completed; advancing to Milestone 5 (Jetpack Compose UI Screens with UI/UX Ultra Pro Max).
- **Verified Deliverables**:
  - Room SQLite database (`AdaDatabase`) with `AlarmEntity`, `DestinationEntity`, and DAOs compiled via KSP.
  - DataStore preference repository (`UserPreferencesRepository`).
  - `AlarmScheduler` interface and `AndroidAlarmScheduler` implementation with `AlarmManager.setAlarmClock()`.
  - Android BroadcastReceivers: `AlarmReceiver`, `BootCompletedReceiver`, `TimeChangeReceiver`.
  - `AlarmPlaybackManager` (audio focus, looping USAGE_ALARM, vibration waveform).
  - `AlarmService` foreground service with full-screen intent to `AlarmActivity`.
  - Full-screen `AlarmActivity` with Compose UI.
  - 21 unit tests passing across calculation, scheduling, recovery, and state transitions.
  - `assembleDebug` APK build verified.

## Decision Log
- **D-01 (Architecture)**: Android app lives in `android/` directory in repository root, keeping backend and web frontend intact.
- **D-02 (SDK Targets)**: Android SDK Platform 36 and Build-Tools 36.0.0 installed; `compileSdk = 36`, `targetSdk = 35` (Android 15), `minSdk = 26` (Android 8.0).
- **D-03 (Alarm Engine)**: Uses `AlarmManager.setAlarmClock()` exclusively for reliable user-facing alarm execution.
- **D-04 (Offline First)**: Room local SQLite database owns the canonical device alarm schedule; backend network failures do not prevent local scheduling.
- **D-05 (Time Representation)**: Stored as canonical epoch milliseconds in UTC (`requiredArrivalEpochMs`, `plannedArrivalEpochMs`, `recommendedLeaveEpochMs`, `recommendedWakeEpochMs`, `scheduledAlarmEpochMs`) to prevent time zone and DST drift.
- **D-06 (Exact Alarm Policy)**: Declares both `SCHEDULE_EXACT_ALARM` (runtime checkable) and `USE_EXACT_ALARM` (permitted by Google Play policy for core alarm clock applications).
- **D-07 (Foreground Service)**: Uses `FOREGROUND_SERVICE_SPECIAL_USE` with `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` declared in manifest for Android 14+ conformance.
