# ADA Smart Alarm — Functional & Non-Functional Requirements

## 1. Domain Calculations
- **REQ-CALC-01**: Given required arrival time, travel duration, preparation time, and safety buffer, compute:
  - `plannedArrivalTime = requiredArrivalTime - safetyBuffer`
  - `recommendedLeaveTime = plannedArrivalTime - travelDuration`
  - `recommendedWakeTime = recommendedLeaveTime - preparationDuration`
- **REQ-CALC-02**: Support overnight / midnight boundary transitions (e.g. required arrival at 1:00 AM with 90 min prep and 45 min travel -> departure previous night at 10:45 PM, wake up at 9:15 PM).
- **REQ-CALC-03**: Handle invalid inputs, past deadlines, negative durations, and zero buffers gracefully with clear validation errors.
- **REQ-CALC-04**: Pure Kotlin implementation independent of Android framework with 100% unit test coverage.

## 2. Local-First Alarm Engine
- **REQ-ALARM-01**: Phone owns alarm schedule. Schedule alarms locally using `AlarmManager.setAlarmClock(AlarmClockInfo, PendingIntent)`.
- **REQ-ALARM-02**: Exact alarm permission verification (`canScheduleExactAlarms()`) and clear explanatory UI directing user to system settings when permission is missing.
- **REQ-ALARM-03**: Full-screen alarm activity (`AlarmActivity`) triggered by high-priority notification with full-screen intent when alarm fires.
- **REQ-ALARM-04**: Alarm sound playback via `RingtoneManager` or `MediaPlayer` using `AudioAttributes.USAGE_ALARM` with looping and audio focus handling.
- **REQ-ALARM-05**: Vibration pattern with `Vibrator` / `VibratorManager`.
- **REQ-ALARM-06**: Dismissal and Snooze actions (configurable snooze duration, default 10 minutes) updating persisted alarm state.
- **REQ-ALARM-07**: Device reboot recovery (`BOOT_COMPLETED` broadcast receiver) to re-arm all enabled future alarms from local database.
- **REQ-ALARM-08**: Time zone and clock change recovery (`TIMEZONE_CHANGED`, `TIME_SET` broadcast receivers).

## 3. Local Persistence
- **REQ-DATA-01**: Room SQLite database persisting:
  - Alarm ID (UUID string)
  - Title / destination name
  - Destination coordinates and address
  - Arrival datetime / time
  - Preparation duration (minutes)
  - Safety buffer (minutes)
  - Travel duration (minutes)
  - Calculated departure and wake times (epoch millis / ISO)
  - Enabled status, trigger status, snooze count
  - Last synced timestamp and sync status
- **REQ-DATA-02**: DataStore for user preferences (default prep duration, default safety buffer, snooze length, sound URI, dark/light theme).

## 4. Jetpack Compose UI/UX
- **REQ-UI-01**: Modern Material 3 design system with polished dark & light palettes, rounded surfaces, legible typography, and calm productivity aesthetics.
- **REQ-UI-02**: Core screens:
  - Home Dashboard: Next active alarm spotlight, recommended wake & leave countdown, quick toggle, list of upcoming alarms.
  - Alarm Creator / Editor: Destination picker, arrival deadline time & date picker, prep time slider, safety buffer slider, live recalculation preview.
  - Active Alarm Screen: Full-screen wake UI, current time, destination reminder, high-contrast Snooze & Dismiss actions.
  - Destination Search & Management: Saved places, recent destinations, manual GPS coordinates entry.
  - Settings & Permissions: Exact alarm status, notification permission status, battery optimization status, sound selection.

## 5. Backend & Firebase Authentication Integration
- **REQ-AUTH-01**: Firebase Authentication integration with session restoration and secure ID token acquisition.
- **REQ-API-01**: Retrofit HTTP client communicating with backend endpoints (`/api/v1/alarms`, `/api/v1/destinations`, `/api/v1/users/me`, `/api/v1/location/geocoding/search`, `/api/v1/location/routes`).
- **REQ-API-02**: Send Firebase Bearer token in `Authorization` header.
- **REQ-SYNC-01**: Bidirectional synchronization between Room local store and backend PostgreSQL when internet is available; local alarm creation NEVER blocked by network failure.
