# ADA Smart Alarm — Cross-Platform Architecture Specification
## Android Preservation + iOS Expansion + Shared FastAPI Backend

---

## 1. Executive Summary & Core Architectural Tenets

ADA Smart Alarm is expanding from an Android-first destination-aware smart alarm system to a cross-platform mobile ecosystem supporting **Android** and **iOS**, while reusing the existing **FastAPI** backend and sharing core **TypeScript** business logic and API contracts.

### Non-Negotiable Tenets:
1. **Preserve Native Android**: The existing native Kotlin + Jetpack Compose application (`android/`) remains a first-class, fully functional Android implementation. It is never overwritten, replaced, or degraded.
2. **Distinct App Identifiers**:
   - Native Android App ID: `com.thinkx.ada`
   - Cross-Platform Mobile Android App ID: `com.thinkx.ada.mobile` (prevents package collision or accidental overwrite on physical devices)
   - Cross-Platform Mobile iOS Bundle ID: `com.thinkx.ada.mobile`
3. **Single Backend Source of Truth**: The FastAPI backend (`backend/app`) provides authoritative routing proxying (Google Maps / Mapbox), user management, alarms, destinations, and sync endpoints.
4. **Platform-Truthful Tracking**: iOS background execution and Android foreground services operate under fundamentally different operating system contracts. We do not pretend they are identical, nor do we rely on non-viable JavaScript timers.
5. **Zero Monorepo Disruption**: Existing web frontend (`frontend/`), native Android (`android/`), and backend (`backend/`) remain in their existing directories. New components are added modularly under `packages/shared/` and `apps/mobile/`.

---

## 2. System Architecture & Directory Layout

```
C:\Users\NEEL\Desktop\thinkx\Alarm\
├── android/                         # [PRESERVED] Native Kotlin + Jetpack Compose Android app (com.thinkx.ada)
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/main/kotlin/com/thinkx/ada/
│   │       ├── alarm/               # AlarmManager.setAlarmClock() & Audio focus
│   │       ├── domain/journey/      # Pure Kotlin DynamicEtaEngine & models
│   │       ├── journey/service/     # Foreground JourneyTrackingService
│   │       └── ui/                  # Jetpack Compose Material 3 screens
│   └── build.gradle.kts
│
├── backend/                         # [PRESERVED] FastAPI + PostgreSQL + Redis + Alembic backend
│   ├── app/
│   │   ├── api/v1/endpoints/       # /alarms, /destinations, /routes, /users, /eta
│   │   ├── integrations/maps/       # Google Maps & Mapbox providers with fallback
│   │   ├── models/                  # SQLAlchemy models
│   │   └── schemas/                 # Pydantic validation schemas
│   └── tests/                       # 131 pytest test suite
│
├── frontend/                        # [PRESERVED] React + Vite web dashboard (unchanged)
│   ├── src/
│   │   ├── core/                    # Web-specific API client, auth & ETA service
│   │   └── pages/                   # Web pages & components
│   └── package.json
│
├── packages/
│   └── shared/                      # [NEW] Reusable pure TypeScript domain logic & contracts
│       ├── src/
│       │   ├── contracts/           # Typed DTOs matching FastAPI schemas
│       │   ├── engine/              # Dynamic ETA calculation engine (ported from DynamicEtaEngine.kt)
│       │   ├── state/               # State machine for journey lifecycle
│       │   ├── geo/                 # Haversine distance, polyline decoding, GPS jump checks
│       │   └── index.ts
│       ├── package.json
│       ├── tsconfig.json
│       └── __tests__/               # Vitest suite for pure domain logic
│
├── apps/
│   └── mobile/                      # [NEW] React Native + TypeScript Expo application
│       ├── app.json                 # Expo config (bundle ID, permissions, plugins)
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   ├── api/                 # Typed API client with token injection & retry
│       │   ├── auth/                # Secure token storage & Firebase Auth session
│       │   ├── components/          # Native UI components (Material/iOS design system)
│       │   ├── navigation/          # React Navigation stacks & tabs
│       │   ├── screens/             # Home, Journey Details, Create/Edit, Diagnostics, Settings
│       │   ├── tracking/            # Platform-abstracted location & tracking manager
│       │   │   ├── LocationService.ts
│       │   │   ├── LocationService.ios.ts
│       │   │   └── LocationService.android.ts
│       │   └── notifications/       # Local notification manager
│       └── __tests__/               # Jest unit tests for mobile components & flows
│
└── docs/                            # [NEW] Architectural specifications & runbooks
    ├── CROSS_PLATFORM_ARCHITECTURE.md
    ├── IOS_BACKGROUND_LOCATION.md
    ├── MOBILE_DEVELOPMENT_SETUP.md
    ├── MOBILE_TEST_PLAN.md
    └── IOS_RELEASE_CHECKLIST.md
```

---

## 3. Component Reuse & Platform-Specific Map

| Component / Layer | Native Android (`android/`) | Web Client (`frontend/`) | Cross-Platform Mobile (`apps/mobile/`) | Shared Package (`packages/shared/`) |
| :--- | :--- | :--- | :--- | :--- |
| **Language / Runtime** | Kotlin / JVM (Java 17) | TypeScript / Browser | TypeScript / React Native (Hermes) | Pure TypeScript (Isomorphic) |
| **UI Framework** | Jetpack Compose + Material 3 | React 19 + Tailwind CSS + Lucide | React Native + Typed Theme Tokens | None |
| **State Management** | StateFlow + ViewModel | Zustand | Zustand / Context | Pure State Machine Types |
| **Local Persistence** | Room (SQLite) + DataStore | LocalStorage | `expo-secure-store` + SQLite/AsyncStorage | Storage Interfaces |
| **Authentication Client** | Firebase Android SDK | Firebase JS SDK (`browserPersistence`) | Firebase JS SDK / REST + SecureStore | Auth User/Session DTOs |
| **API Networking** | Retrofit + OkHttp | Axios | Axios / Fetch Client | Endpoint schemas & DTOs |
| **Background Location** | Foreground Service (`location`) | Not supported | iOS: CoreLocation / `expo-location`<br>Android: Foreground Service | GPS validation & filtering math |
| **Alarms & Scheduling** | `AlarmManager.setAlarmClock()` | Not supported | `expo-notifications` local triggers | Lead-time calculation formulas |
| **ETA Mathematical Engine** | `DynamicEtaEngine.kt` | `ETACalculationService.ts` | Shared Engine | `DynamicEtaEngine.ts` |
| **Polyline & Deviation** | Pure Kotlin math | Leaflet / Pure math | Shared Engine | Pure TS polyline decoder & corridor math |

---

## 4. API Endpoint Reuse & Network Contracts

The cross-platform mobile application communicates with the existing FastAPI backend (`backend/app/api/v1`):

| Method | Endpoint | Purpose | Mobile Usage | Idempotency |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/users/me` | Fetch authenticated user profile | App bootstrap & session verification | Read-only |
| `GET` | `/destinations` | List user's saved/recent destinations | Destination picker in Journey creation | Read-only |
| `POST` | `/destinations` | Save new destination | Add destination from search/map | Standard POST |
| `GET` | `/alarms` | List all journeys/alarms | Home dashboard active & upcoming list | Read-only |
| `POST` | `/alarms` | Schedule new journey/alarm | Journey creator form | `X-Idempotency-Key` header |
| `GET` | `/alarms/{id}` | Get specific journey details | Live tracking screen & detail view | Read-only |
| `PATCH`| `/alarms/{id}` | Update journey schedule or details | Journey editor & rescheduling | Optimistic / Safe PATCH |
| `DELETE`| `/alarms/{id}`| Cancel/delete journey | Cancel Journey action | Idempotent DELETE |
| `POST` | `/alarms/{id}/enable` | Enable/re-arm journey | Journey toggle | Safe action |
| `POST` | `/alarms/{id}/disable`| Disable journey | Journey toggle | Safe action |
| `POST` | `/routes` | Proxy live Google/Mapbox route & traffic | Initial calculation & route refresh | Rate-limited + Redis cached |
| `GET` | `/location/health` | Provider infrastructure health | Diagnostics & fallback status banner | Read-only |
| `POST` | `/geocoding/search` | Destination address lookup | Place search autocomplete | Rate-limited |
| `POST` | `/geocoding/reverse`| Address from GPS fix | Reverse geocode current location | Privacy-fuzzed (~11m) |

---

## 5. Network Address & Development Configurations

Mobile devices and simulators access backend development servers differently:

| Platform | Host Target | Base URL Configuration |
| :--- | :--- | :--- |
| **Android Emulator** | Localhost alias | `http://10.0.2.2:8000/api/v1/` |
| **iOS Simulator** | Host Mac loopback | `http://localhost:8000/api/v1/` |
| **Physical Android Phone** | LAN IP or Tunnel | `http://192.168.x.x:8000/api/v1/` or HTTPS Tunnel |
| **Physical iPhone** | LAN IP or Tunnel | `http://192.168.x.x:8000/api/v1/` or HTTPS Tunnel |
| **Staging Environment** | Staging Cloud Server | `https://staging-api.ada-alarm.app/api/v1/` |
| **Production** | Production Cloud Cluster | `https://api.ada-alarm.app/api/v1/` |

---

## 6. Authentication & Secure Storage Architecture

1. **Authentication Flow**:
   - The user signs in via Email/Password or Federated Sign-In.
   - Mobile client obtains Firebase ID Token.
   - Client sends `Authorization: Bearer <id_token>` on all requests.
   - FastAPI dependency `get_current_user` validates token cryptographically against Firebase JWKS, extracts UID, and upserts user in PostgreSQL.
2. **Token Security**:
   - Web uses browser cookies/indexedDB.
   - Native Android uses Android Keystore / EncryptedSharedPreferences.
   - React Native mobile app uses `expo-secure-store` (iOS Keychain with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`, Android KeyStore AES-256).
   - Sensitive tokens are **never** stored in plaintext `AsyncStorage`.
   - Proactive refresh is triggered before expiration; 401 triggers single-flight retry with freshly retrieved token.

---

## 7. Journey Tracking Mathematical Contract

The core mathematical invariants established in `DynamicEtaEngine.kt` are mirrored identically in `packages/shared/src/engine/DynamicEtaEngine.ts`:

1. **Lead Time Calculation**:
   $$\text{TrackingStartEpochMs} = \text{ScheduledDepartureEpochMs} - (\text{LeadTimeMinutes} \times 60 \times 1000)$$
   *(Default lead time: 15 minutes)*

2. **Fix Validation**:
   - Max horizontal accuracy: $\le 50\text{ m}$
   - Max fix age: $\le 60\text{ seconds}$
   - Future timestamp rejection: $t_{\text{fix}} \le t_{\text{current}} + 5000\text{ ms}$

3. **GPS Velocity Jump Protection**:
   - Implied velocity: $v = \frac{\Delta d}{\Delta t}$
   - If $v > 45\text{ m/s}$ (~$162\text{ km/h}$) and accuracy $> 15\text{ m}$, fix is rejected as an unrealistic jump.

4. **Traffic-Aware ETA Derivation**:
   $$\text{PredictedArrivalEpochMs} = t_{\text{fix}} + (\text{RemainingDurationSeconds} \times 1000)$$
   *Elapsed travel time is never double-counted.*
   *No artificial stop penalty is superimposed on live provider traffic duration.*

5. **Route Recalculation Hysteresis**:
   - Request cooldown: Minimum 30 seconds between provider queries.
   - Trigger immediately if route deviation confirmed ($d_{\text{min}} > 250\text{ m}$).
   - Trigger if progress $\ge 200\text{ m}$ AND elapsed time $\ge 180\text{ seconds}$.
   - Trigger if ETA stale ($\ge 300\text{ seconds}$).

6. **Alert Thresholds**:
   - Approaching alert: $d \le 1,000\text{ m}$ (triggered exactly once per journey).
   - Arrival confirmation: $d \le 100\text{ m}$ with $\ge 2$ consecutive accurate fixes ($\le 50\text{ m}$).
