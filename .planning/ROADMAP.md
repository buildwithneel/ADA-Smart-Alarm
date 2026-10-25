# ADA Smart Alarm — Implementation Roadmap

## Milestones Overview

### Milestone 1: Workspace Audit, Toolchain & Foundation Verification
- **Goal**: Verify environment, Java/Gradle toolchains, install Android SDK 35 & build-tools, audit existing FastAPI backend, verify API contracts.
- **Status**: IN PROGRESS / NEARLY COMPLETE.
- **Deliverables**:
  - Android project scaffolded in `/android` with AGP 9.0.1, Kotlin 2.3, compileSdk 35, Java 17 toolchain.
  - Gradle wrapper verification and build pipeline baseline.
  - `.planning/` artifacts (PROJECT, REQUIREMENTS, ROADMAP, STATE).

### Milestone 2: Domain Engine & Pure Calculation Unit Tests
- **Goal**: Implement `AdaCalculationEngine` with the exact mathematical formulation, handling overnight schedules, safety buffers, preparation time, traffic buffers, and date boundaries.
- **Deliverables**:
  - `AdaCalculationEngine.kt` and supporting data models (`CalculationInput`, `CalculationResult`, `TimeUtils`).
  - Comprehensive unit test suite covering normal cases, overnight/midnight crossings, leap seconds, zero buffers, invalid inputs, and historical comparisons.

### Milestone 3: Local Persistence Layer (Room + DataStore)
- **Goal**: Implement local SQLite storage using Room for offline-first resilience.
- **Deliverables**:
  - `AlarmEntity`, `DestinationEntity`, `AlarmHistoryEntity`.
  - Room DAOs: `AlarmDao`, `DestinationDao`.
  - `AdaDatabase` with migrations and converters.
  - DataStore preference repository for user settings.
  - Unit tests for DAOs and database operations.

### Milestone 4: Native Android Alarm Engine (AlarmManager, Receivers & Audio)
- **Goal**: Implement reliable local alarm scheduling and ringing mechanics.
- **Deliverables**:
  - `AndroidAlarmScheduler` using `AlarmManager.setAlarmClock()`.
  - `AlarmReceiver` broadcast receiver.
  - `BootCompletedReceiver` for re-arming alarms after device restart.
  - `TimeChangedReceiver` for clock/timezone adjustments.
  - `AlarmRingtoneService` / `AlarmPlaybackManager` for alarm audio and vibration with audio focus.
  - Exact alarm permission management helper.

### Milestone 5: Jetpack Compose Design System & UI Screens (UI/UX Ultra Pro Max)
- **Goal**: Deliver a polished, modern, calm Material 3 design system and core screens.
- **Deliverables**:
  - Theme, Color, Typography, Shapes (`AdaTheme`).
  - Home Dashboard with Next Alarm spotlight, countdown, upcoming alarms list.
  - Alarm Creator / Editor with dynamic calculations preview, time pickers, sliders.
  - Full-screen `AlarmActivity` with high-contrast Snooze & Dismiss gestures.
  - Destination management screen and Settings screen.

### Milestone 6: Backend Integration, Firebase Authentication & API Sync
- **Goal**: Integrate native Android app with existing FastAPI backend and Firebase Auth.
- **Deliverables**:
  - Retrofit HTTP client with Bearer token authenticator.
  - DTOs matching backend Pydantic schemas.
  - Sync repository that syncs local Room alarms with backend without blocking local creation.
  - Geocoding and route calculation backend integration.

### Milestone 7: Verification, Code Review & Release Quality
- **Goal**: End-to-end integration testing, code review, linting, and final verification report.
- **Deliverables**:
  - Automated tests passing.
  - Verification checklist for lock screen, backgrounding, reboot, offline delivery.
  - Complete documentation and build summary.
