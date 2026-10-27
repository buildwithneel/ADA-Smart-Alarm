# ADA Mobile Cross-Platform Verification & Test Plan
## Layered Testing Strategy for Android, iOS, Shared Core & Backend

---

## 1. Testing Pyramid Overview

```
              ┌──────────────────────────┐
              │ Physical Device / Field  │ (GPS accuracy, battery, background alerts)
              ├──────────────────────────┤
              │ Simulator / E2E Flows    │ (Screen navigation, auth, permissions)
              ├──────────────────────────┤
              │ Mobile App Component UI  │ (Loading, empty, error, form validation)
              ├──────────────────────────┤
              │ Shared TypeScript Core   │ (Math engine, polyline, jump detection)
              ├──────────────────────────┤
              │ Backend Regression Tests │ (FastAPI contracts, routing, idempotency)
              └──────────────────────────┘
```

---

## 2. Test Execution Matrix by Layer

### Layer A: Shared TypeScript Core (`packages/shared/`)
- **Tool**: Vitest
- **Scope**:
  1. `DynamicEtaEngine.test.ts`:
     - Verification against canonical Charusat 9:00 AM scenario.
     - Tracking start epoch ms calculation with default 15-minute lead time.
     - Location fix validation: reject stale (>60s), inaccurate (>50m), and future fixes.
     - GPS velocity jump detection: reject speeds > 45 m/s with accuracy > 15m; permit high-accuracy highway transitions.
     - Traffic-aware ETA calculation: duration from provider added to fix timestamp; verify elapsed travel time is never double-counted.
     - Fallback Great-Circle heuristic calculation: labeled explicitly as non-traffic.
     - Polyline decoding and route corridor deviation (>250m).
     - Approaching destination alert (<= 1,000m, idempotent single-trigger).
     - Arrival confirmation (<= 100m, accurate fix <= 50m, requires 2 consecutive hits).
  2. `JourneyStateMachine.test.ts`:
     - Valid state transitions: `SCHEDULED` -> `READY_TO_TRACK` -> `ACTIVE_TRACKING` -> `APPROACHING` -> `ARRIVED`.
     - Degraded state handling (`TRACKING_DEGRADED` on inaccurate fixes).
     - Cancellation and terminal states.

### Layer B: Mobile Application Tests (`apps/mobile/`)
- **Tool**: Jest + React Native Testing Library
- **Scope**:
  1. `AuthSession.test.ts`: Session restoration from `expo-secure-store`, token refresh on 401.
  2. `HomeScreen.test.tsx`: Upcoming journeys display, active journey spotlight card, empty state.
  3. `CreateJourneyScreen.test.tsx`: Date/time picker, destination selector, validation preventing past departure.
  4. `JourneyDetailScreen.test.tsx`: Live ETA telemetry, traffic status badge, manual Start/Stop controls.
  5. `PermissionDiagnostics.test.tsx`: Location and notification status banners, deep link to settings.
  6. `LocationService.test.ts`: Mocked platform adapter verifying foreground vs background location call sequence.

### Layer C: Preserved Native Android Verification (`android/`)
- **Tool**: Gradle / JUnit 4 / MockK
- **Execution**: `.\gradlew.bat testDebugUnitTest` (97 unit tests passing).
- **Scope**:
  - `AdaCalculationEngineTest`: Wake/leave/arrival math.
  - `DynamicEtaEngineTest`: Dynamic ETA calculations in Kotlin.
  - `JourneyLifecycleAndCoordinatorTest`: Coordinator location fix processing, deviation, arrival.
  - `AlarmSchedulerTest` & `AlarmRecoveryManagerTest`: Exact alarms and reboot recovery.
  - `RoomMigrationTest`: Non-destructive schema migrations.
  - `HomeViewModelTest`, `AuthViewModelTest`, `AlarmSyncRepositoryTest`.

### Layer D: Backend Regression Verification (`backend/`)
- **Tool**: Pytest
- **Execution**: `python -m pytest` (131 tests passing).
- **Scope**:
  - `test_location_and_routing.py`: Route calculation, provider fallback, geocoding.
  - `test_alarms.py` & `test_sync.py`: Alarms CRUD, `X-Idempotency-Key` deduplication.
  - `test_auth.py`: Token verification, user isolation.
  - `test_eta_engine.py` & `test_dynamic_eta_recalculation.py`: Dynamic recalculation triggers.

### Layer E: Physical Device & OS Verification
- **Android Validation**:
  - Verify `com.thinkx.ada` native app and `com.thinkx.ada.mobile` React Native app install side-by-side with zero collision.
  - Test screen lock and persistent notification during tracking.
- **iOS Validation (requires macOS & iPhone)**:
  - Verify `UIBackgroundModes: ["location"]` in built `.ipa`.
  - Permission dialog flow: WhenInUse -> Always Allow.
  - Background location indicator (blue pill / status bar) during active journey.
  - Screen locked tracking: alert firing when approaching (1 km) and arriving (100 m).
  - Force-quit truthfulness verification: confirm tracking stops on user swipe-to-kill.
