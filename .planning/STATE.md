# Project Memory & Current State

## Current Position
- **Active Milestone**: Milestone 5 completed; advancing to Milestone 6 (Backend Integration, Firebase Authentication & API Sync).
- **Verified Deliverables**:
  - Jetpack Compose + Material 3 UI screens implemented:
    - Home Dashboard (`HomeScreen`, `HomeViewModel`): Next Alarm spotlight card with countdown, upcoming alarms list from Room Flow, toggle controls synchronized with `AlarmScheduler`, exact-alarm permission banner.
    - Create/Edit Alarm (`CreateEditAlarmScreen`, `CreateEditAlarmViewModel`): Destination selection with saved/recent quick chips, arrival date/time pickers, duration sliders, live calculation preview card matching `AdaCalculationEngine`, validation preventing past schedules, permission denial & failure handling.
    - Destination Management (`DestinationsScreen`, `DestinationsViewModel`): Saved destinations and recent destinations list, add/edit modal, delete confirmation.
    - Settings (`SettingsScreen`, `SettingsViewModel`): Default preparation, safety buffer, snooze durations, Theme preference (System/Dark/Light), vibration switch, exact alarm and notification permission status & settings shortcuts.
  - `AdaApplication` application class managing repository and scheduler singletons.
  - Complete 47 unit tests passing across calculations, scheduler, recovery, state transitions, and all 4 ViewModels.
  - `assembleDebug` APK build verified (`app-debug.apk`).


## Decision Log
- **D-01 (Architecture)**: Android app lives in `android/` directory in repository root, keeping backend and web frontend intact.
- **D-02 (SDK Targets)**: Android SDK Platform 36 and Build-Tools 36.0.0 installed; `compileSdk = 36`, `targetSdk = 35` (Android 15), `minSdk = 26` (Android 8.0).
- **D-03 (Alarm Engine)**: Uses `AlarmManager.setAlarmClock()` exclusively for reliable user-facing alarm execution.
- **D-04 (Offline First)**: Room local SQLite database owns the canonical device alarm schedule; backend network failures do not prevent local scheduling.
- **D-05 (Time Representation)**: Stored as canonical epoch milliseconds in UTC (`requiredArrivalEpochMs`, `plannedArrivalEpochMs`, `recommendedLeaveEpochMs`, `recommendedWakeEpochMs`, `scheduledAlarmEpochMs`) to prevent time zone and DST drift.
- **D-06 (Exact Alarm Policy)**: Declares both `SCHEDULE_EXACT_ALARM` (runtime checkable) and `USE_EXACT_ALARM` (permitted by Google Play policy for core alarm clock applications).
- **D-07 (Foreground Service)**: Uses `FOREGROUND_SERVICE_SPECIAL_USE` with `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` declared in manifest for Android 14+ conformance.
