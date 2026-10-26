# ADA — Destination-Aware Smart Alarm & Dynamic Journey Tracking Platform

<div align="center">

![ADA Smart Alarm](https://img.shields.io/badge/ADA-Dynamic%20Journey%20Tracking-2563EB?style=for-the-badge&logo=google-maps&logoColor=white)
![Android Native](https://img.shields.io/badge/Android-Kotlin%20%7C%20Compose-3DDC84?style=for-the-badge&logo=android&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-Authentication-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![React 19](https://img.shields.io/badge/React-19%20%7C%20Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)

**A reliable, destination-aware journey monitoring and dynamic ETA alert platform.**  
*Schedule your journey; ADA prepares and begins background GPS monitoring near departure, continuously updates ETA using live traffic, reroutes on deviations, alerts on approach, and confirms arrival.*

</div>

---

## 🌟 The Vision: Beyond Fixed Alarm Clocks

Conventional alarms ring at a static time regardless of road conditions. Early smart alarms merely computed a static wake-up time before a trip.

**ADA is fundamentally different:**  
A user schedules a journey and departure time. ADA automatically prepares and starts monitoring the journey near departure (~15 minutes prior), tracks the user's GPS position in the background via an Android Foreground Service (~60s interval), continuously recalculates arrival times using live route and traffic data, automatically reroutes on deviation, alerts the user when approaching the destination, and confirms arrival.

```
Scheduled Departure: 7:00 AM (Vadodara) ──> Destination: Ahmedabad RTO
   │
   ├── 6:45 AM (T - 15m)   : Automatic tracking startup via AlarmManager & Foreground Service
   ├── 7:05 AM (Traffic +) : Live ETA dynamically shifts later from 9:00 AM to 9:14 AM
   ├── 7:35 AM (Deviation) : User turns off route; ADA detects cross-track error > 250m & reroutes
   ├── 8:50 AM (Proximity) : Approaching threshold reached (<= 1,000m) -> Idempotent alert fires
   └── 9:02 AM (Arrival)   : Physical arrival confirmed (<= 100m over consecutive fixes) -> Tracking stops
```

---

## 🏗️ Full-Stack System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          NATIVE ANDROID CLIENT (Kotlin & Compose)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  UI Layer:           Jetpack Compose • Navigation 3 • Spotlight Journey Card           │
│  State Management:   StateFlow • ViewModel • Coroutines                                │
│  Coordination:       JourneyTrackingCoordinator • DynamicEtaEngine                     │
│  Background Engine:  JourneyTrackingService (foregroundServiceType="location")         │
│  Exact Scheduling:   AndroidJourneyScheduler (AlarmManager.setAlarmClock)              │
│  Local Persistence:  Room v3 (Non-destructive migrations 1->2->3) • DataStore         │
│  Routing Layer:      CompositeRoutingProvider (Backend Proxy -> Offline Haversine)     │
└───────────────────────────────────────────▲────────────────────────────────────────────┘
                                            │ HTTPS / Retrofit (Bearer JWT)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND GATEWAY                                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  Authentication:     Firebase Admin SDK (Token verification & user claims)             │
│  Routing Service:    ResilientRoutingProvider (Google Maps API + Mapbox Navigation)    │
│  Cache & Broker:     Redis 7 (5-minute traffic route cache, distributed locks)         │
│  Database Layer:     PostgreSQL 15 + SQLAlchemy 2.0 + Alembic Migrations               │
│  Sync Engine:        Two-Way Client Sync (alarms, destinations, version tracking)      │
│  Background Workers: Celery 5.3 + Celery Beat (traffic sweep & notification dispatch)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Capabilities & Engineering Highlights

### 1. 📍 Native Android Foreground Tracking & Scheduled Startup
* **Exact Alarm Wakeup:** Uses `AlarmManager.setAlarmClock()` to wake the device from Android Doze mode at `scheduledDeparture - leadTime` (default: 15 minutes before departure).
* **Location Foreground Service:** Tracks movement using `LocationManager` (GPS + Network) with a target 60-second update interval under `foregroundServiceType="location"`.
* **Persistent Notification:** Maintains an ongoing, non-intrusive Android notification displaying destination name, live dynamic ETA, remaining distance, and traffic state.
* **Degraded Tracking Communication:** If GPS signal is lost or delayed by OEM battery policies for > 120s, the UI honestly transitions to a `TRACKING_DEGRADED` state instead of showing false live data.

### 2. 🧮 Pure Dynamic ETA Calculation Engine
The domain engine ([DynamicEtaEngine.kt](file:///android/app/src/main/kotlin/com/thinkx/ada/domain/journey/engine/DynamicEtaEngine.kt)) is completely decoupled from Android platform classes:
* **No Double-Counting:** 
  $$\text{predictedArrival} = \text{currentFix.timestamp} + (\text{providerDurationSeconds} \times 1,000)$$
  Elapsed travel time is **never** added to provider-returned remaining durations, and static stop penalties are **never** double-counted on top of live traffic durations.
* **GPS Velocity Jump Protection:** Validates coordinates $[-90, 90] / [-180, 180]$, rejects accuracy $> 50\text{m}$, rejects stale fixes $> 60\text{s}$, and filters velocity jumps $> 45\text{ m/s}$ ($162\text{ km/h}$) to guard against urban-canyon GPS drift.
* **Throttling & Hysteresis:** Routing requests are throttled (minimum 120s or 500m movement) to protect battery and provider API quotas.

### 3. 🔄 Automatic Route Deviation Detection & Recalculation
* **Cross-Track Distance:** Continuously measures the user's distance to the planned route polyline segments.
* **Automatic Reroute:** When distance exceeds $250\text{ meters}$, ADA marks the state as `RECALCULATING` and requests fresh directions from the current coordinate to the destination.

### 4. 🔔 Multi-Stage Proximity Alerts
* **Approaching Destination Alert:** Fires once when within $1,000\text{ meters}$ of the destination. Idempotently persisted in Room (`isApproachingAlertSent = true`) to prevent spamming across process restarts.
* **Verified Arrival Confirmation:** Requires the user to enter the $100\text{ meter}$ arrival geofence across at least **2 consecutive reliable fixes** (accuracy $\le 50\text{m}$). Upon arrival, active tracking cleanly terminates and resources are released.

### 5. 🛡️ Non-Destructive Room Migration Strategy
User data is guaranteed to survive application upgrades. [AdaDatabase.kt](file:///android/app/src/main/kotlin/com/thinkx/ada/data/local/AdaDatabase.kt) provides explicit migrations:
* **`MIGRATION_1_2`:** Adds two-way synchronization columns (`serverId`, `syncStatus`, `lastSyncedEpochMs`).
* **`MIGRATION_2_3`:** Adds journey tracking columns (`scheduledDepartureEpochMs`, `trackingLeadMinutes`, `approachingThresholdMeters`, `arrivalThresholdMeters`, `currentEtaEpochMs`, `remainingDistanceMeters`, etc.) and automatically backfills `scheduledDepartureEpochMs = scheduledAlarmEpochMs`.
* **`MIGRATION_1_3`:** Seamless upgrade chain for legacy v1 installs. Tested by [RoomMigrationTest.kt](file:///android/app/src/test/kotlin/com/thinkx/ada/data/local/RoomMigrationTest.kt).

### 6. 🌐 Resilient Multi-Provider Routing Architecture
* **Primary:** FastAPI backend proxies Google Maps Directions and Mapbox Navigation with live traffic models (`departure_time=now`). API secrets never reside on mobile devices.
* **Offline Fallback:** [FallbackRoutingProvider.kt](file:///android/app/src/main/kotlin/com/thinkx/ada/domain/journey/routing/FallbackRoutingProvider.kt) computes distance via Haversine geometry with an assumed speed of $40\text{ km/h}$.
* **Transparent ETA Labeling:** Fallbacks are explicitly surfaced in the UI with a `"FALLBACK ESTIMATE"` chip; live traffic results display `"LIVE TRAFFIC"`.

---

## 📂 Project Structure

```
Alarm/
├── android/                         # Native Android Application (Kotlin & Compose)
│   ├── app/
│   │   ├── src/main/kotlin/com/thinkx/ada/
│   │   │   ├── auth/                # SessionManager & Firebase Auth integration
│   │   │   ├── data/
│   │   │   │   ├── local/           # Room Database, DAOs, Entities, and Migrations
│   │   │   │   └── sync/            # Two-way AlarmSyncWorker & SyncRepository
│   │   │   ├── domain/journey/      # Pure Kotlin journey models, engine, and contracts
│   │   │   │   ├── engine/          # DynamicEtaEngine (pure math & validation)
│   │   │   │   ├── model/           # JourneySchedule, LocationFix, DynamicEtaResult
│   │   │   │   └── routing/         # RoutingProvider, Backend & Fallback providers
│   │   │   ├── journey/             # Android Platform Tracking Integration
│   │   │   │   ├── receiver/        # JourneyStartReceiver (AlarmManager wakeup)
│   │   │   │   ├── repository/      # JourneyTrackingCoordinator
│   │   │   │   ├── scheduler/       # AndroidJourneyScheduler (exact alarms)
│   │   │   │   └── service/         # JourneyTrackingService (foreground GPS)
│   │   │   ├── network/             # Retrofit DTOs & AdaApiService
│   │   │   └── ui/                  # Jetpack Compose Screens (Home, Create, Settings)
│   │   └── src/test/kotlin/         # 91 Automated Unit & Integration Tests
│   └── build.gradle.kts
│
├── backend/                         # FastAPI Application Gateway (Python 3.10+)
│   ├── app/
│   │   ├── api/v1/endpoints/        # REST routes (alarms, routes, sync, auth, health)
│   │   ├── core/                    # Security, database, errors, and configuration
│   │   ├── integrations/maps/       # Google Maps & Mapbox resilient providers
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic v2 validation contracts
│   │   └── services/                # RoutingService, ETACalculationService
│   ├── migrations/                  # Alembic database migrations
│   └── tests/                       # Pytest test suite (auth, sync, routing)
│
└── frontend/                        # Web Management Console (React 19 + Vite)
    └── src/                         # TypeScript components, hooks, and pages
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Android:** Android Studio Ladybug / Koala, Android SDK 35, JDK 17+.
- **Backend:** Python 3.10+, PostgreSQL 15+, Redis 7+.
- **Web (Optional):** Node.js 20+, npm / pnpm.

---

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL, Redis, Firebase, and Map API keys

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 3. Android Application Setup & Build

1. Open `android/` in Android Studio.
2. In `app/src/main/res/values/strings.xml` (or `local.properties`), configure the backend URL:
   - For Android Emulator: `http://10.0.2.2:8000/api/v1/`
   - For Physical Device: `http://<YOUR_LAN_IP>:8000/api/v1/`
3. Execute unit tests:
   ```bash
   cd android
   ./gradlew testDebugUnitTest
   ```
4. Build the Debug APK:
   ```bash
   ./gradlew assembleDebug
   ```
   *Artifact generated at:* `android/app/build/outputs/apk/debug/app-debug.apk`

---

## 🧪 Automated Testing & Verification

| Test Suite | Scope | Tests Run | Result |
| :--- | :--- | :---: | :---: |
| **Android Unit Tests** | `DynamicEtaEngineTest`, `JourneyLifecycleTest`, `RoomMigrationTest`, Auth & Sync | **91** | **PASSED (100%)** |
| **Android Debug APK** | Full Gradle compilation & packaging (`assembleDebug`) | **39 Tasks** | **SUCCESS** |
| **Backend Pytest** | Firebase Auth JWT verification, two-way sync, location & resilient routing | **29** | **PASSED (100%)** |

---

## 📱 Manual Testing Checklist for Physical Android Devices

1. **Permissions:** Launch ADA on Android 13+. Verify notification and precise location permissions (`ACCESS_FINE_LOCATION`) are granted.
2. **Scheduled Start:** Create a journey departing in 20 minutes with a 15-minute lead time. Lock the device. Verify that in 5 minutes the device wakes up and posts the ongoing `ADA Journey Tracking` notification.
3. **Background Location:** Travel along the route. Verify the ETA and remaining distance update every ~60 seconds on the lock-screen notification.
4. **Route Deviation:** Turn off the planned path (> 250m). Verify the card updates to `🔄 RECALCULATING`, followed by an updated route and ETA within 15 seconds.
5. **Approaching Alert:** Approach within 1,000m of the destination. Verify a heads-up notification and audio chime fire once.
6. **Confirmed Arrival:** Reach the destination coordinate (< 100m). Verify the `You Have Arrived!` alert appears and background tracking shuts down cleanly.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](file:///LICENSE) file for details.
