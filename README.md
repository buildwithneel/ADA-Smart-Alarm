# ADA — Adaptive Dynamic Alarm Platform

<div align="center">

![ADA Smart Alarm](https://img.shields.io/badge/ADA-Adaptive%20Dynamic%20Alarm-blue?style=for-the-badge&logo=alarm)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React 19](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**The intelligent, location-aware smart alarm that wakes you up dynamically based on real-time traffic, weather, calendar schedules, and morning routines.**

</div>

---

## 🌟 What is ADA?

Standard alarms ring at a fixed hour regardless of whether traffic is gridlocked or the roads are empty. **ADA (Adaptive Dynamic Alarm)** flips the equation:

> *"I need to arrive at CHARUSAT at 9:00 AM."*

ADA continuously analyzes your morning journey to calculate precisely when to wake you up and when to leave:

$$\text{Wake Time} = \text{Target Arrival} - \text{Travel Duration (Live Traffic)} - \text{Preparation Time} - \text{Safety Buffer} - \text{Weather Buffer}$$

If heavy rain or a sudden traffic jam adds 18 minutes to your commute, ADA automatically recalculates your schedule and wakes you earlier so you are never late.

---

## 🏗️ System Architecture

```
                                      +-----------------------------------------+
                                      |   Client Frontend (React 19 + Vite)     |
                                      |   Zustand • TanStack Query • Tailwind   |
                                      +--------------------+--------------------+
                                                           | (HTTPS / REST)
                                                           v
                                      +-----------------------------------------+
                                      |         FastAPI ASGI Gateway            |
                                      |   Request Tracing • Security Headers    |
                                      |   Content Limit (2MB) • Rate Limiting   |
                                      +---------+---------------------+---------+
                                                |                     |
                        +-----------------------+                     +-----------------------+
                        v                                                                     v
       +-----------------------------------+                                 +-----------------------------------+
       |          Domain Services          |                                 |       Background Workers          |
       |  • ETACalculatorService           |                                 |  • Celery Beat (Periodic Sweeps)  |
       |  • SmartAlarmEngine               |                                 |  • Celery Workers (Prefetch=1)    |
       |  • AlarmRecalculationService      |                                 |  • Outage Reconciler              |
       |  • Context & Weather Intelligence |                                 |  • Web Push Notification Delivery |
       |  • AIAssistantService (Gemini)    |                                 +-----------------+-----------------+
       |  • PersonalizationService         |                                                   |
       +----------------+------------------+                                                   v
                        |                                                    +-----------------------------------+
                        v                                                    |      Redis Cache & Broker         |
       +-----------------------------------+                                 |  • Distributed Locks              |
       |         Repository Layer          |                                 |  • Route & Geocode TTL Cache      |
       |  • User • Destination • Alarm     |                                 |  • Task Message Broker (AOF)      |
       |  • Notification • Calendar        |                                 +-----------------------------------+
       |  • AssistantConversation / Draft  |
       +----------------+------------------+
                        |
                        v
       +-----------------------------------+          +----------------------------------------------------------+
       |   PostgreSQL Relational DB (15+)  |          |                  External Integrations                   |
       |   Composite Performance Indexes   | <------> |  • Maps: Google Directions & Mapbox (Failover)           |
       |   Connection Pooling & Recycled   |          |  • Auth: Firebase Admin SDK (JWKS Verification)          |
       |   Cascading Deletions (GDPR)      |          |  • Push: VAPID / Web Push Protocol                       |
       +-----------------------------------+          |  • Context: Open-Meteo API & Google Calendar OAuth       |
                                                      |  • AI: Google Gemini 1.5 Flash / OpenAI Engine           |
                                                      +----------------------------------------------------------+
```

---

## ⚡ Core Capabilities

### 1. 📍 Intelligent Geocoding & Routing Engine
* **Multi-Provider Fallback:** Seamless primary/fallback routing between Google Maps Directions and Mapbox Directions.
* **Smart Route Caching:** Geocoding results cached for 24 hours; traffic routes cached for 5 minutes to balance freshness and API quotas.
* **Haversine Math Fallback:** Guaranteed heuristic computation if all external routing providers are unavailable.

### 2. 🚦 Dynamic Traffic Sweeps & Automatic Recalculation
* **Active Window Monitoring:** Periodically monitors all alarms departing within 4 hours.
* **Schedule Churn Prevention:** Only triggers wake-up recalculations if the ETA shifts by $\ge 3$ minutes.
* **Distributed Locking & Concurrency:** Optimistic version checking (`schedule_version`) with Redis distributed locks prevents race conditions.
* **Audit Trail:** Every schedule change records previous wake time, new wake time, and human-readable reason in `alarm_schedule_changes`.

### 3. 🔔 Web Push Notification & Delivery Engine
* **VAPID-Authenticated Push:** Standard Web Push protocol delivering reminders to mobile and desktop browsers.
* **Channel Flexibility:** In-app alerts, browser pushes, and departure reminders.
* **Worker Resilience:** Automatic exponential backoff retries on transient errors; past-due notifications are superseded rather than waking users hours late.

### 4. ⛅ Weather Context & Google Calendar Intelligence
* **Adverse Weather Buffers:** Automatically queries Open-Meteo forecasts; detects rain, snow, or adverse conditions and applies safety buffers (default +10 mins, up to +30 mins).
* **Two-Way Google Calendar Sync:** Ingests calendar events with destination locations and converts them directly into smart adaptive alarms.

### 5. 🤖 AI Natural Language Assistant
* **Natural Conversation:** Create, query, modify, or cancel alarms using natural language (e.g., *"I have an interview at CHARUSAT tomorrow at 9 AM. I need 30 minutes to get ready and 10 minutes buffer."*).
* **Deterministic Engine Binding:** The AI extracts intent and structured entities; calculations are executed by the verified deterministic ETA engine.
* **Confirmation Safety Guard:** The AI creates a structured draft; alarms are only scheduled after explicit user confirmation.

### 6. 🧠 Personalization Engine
* **Behavioral Learning:** Tracks user departure punctuality and preparation habits.
* **Adaptive Buffers:** Automatically recommends customized preparation times and safety buffers tailored to user routines.

### 7. 🛡️ Production Security & Hardening
* **Non-Root Containers:** Backend runs as unprivileged user `ada` (UID 10001).
* **Cryptographic Token Verification:** Strict Firebase Admin token validation (issuer, audience, expiry, signature).
* **Mock Token Guard:** Mock test tokens are unconditionally rejected when deployed in production.
* **Object-Level RBAC:** Every user-owned entity enforces ownership validation to prevent IDOR attacks.
* **Defensive HTTP Headers:** Injected HSTS (1-year preload), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and CSP.
* **DOS Protection:** Rejects payloads `> 2MB` with `HTTP 413 Payload Too Large`.
* **GDPR Compliance:** Full data portability (`GET /api/v1/users/me/data`) and account erasure (`DELETE /api/v1/users/me`).

### 8. 📊 Observability & Operations
* **Structured JSON Logging:** Emits RFC 8259 single-line JSON logs with secret/token redaction.
* **Prometheus Metrics:** Standard `/metrics` endpoint exposing runtime, database connection pool, and queue telemetry.
* **Dedicated Health Probes:** `/health/live` (liveness), `/health/ready` (readiness), and `/health/deps` (dependency latency).

---

## 📂 Repository Directory Layout

```
ADA-Smart-Alarm/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI (FastAPI, Postgres, Redis, Vite, Docker)
├── backend/
│   ├── Dockerfile                 # Multi-stage production container (Non-root 'ada' user)
│   ├── alembic.ini                # Alembic database configuration
│   ├── requirements.txt           # Pinned production Python dependencies
│   ├── .env.example               # Backend environment reference
│   ├── app/
│   │   ├── api/v1/                # Versioned REST API endpoints (Alarms, Users, Maps, AI, Health)
│   │   ├── core/                  # Config, Database pooling, Middlewares, Rate Limiting, Security
│   │   ├── models/                # SQLAlchemy 2.0 entities (User, Alarm, Destination, Drafts)
│   │   ├── repositories/          # Optimized data access layer with composite indexes
│   │   ├── schemas/               # Pydantic v2 schemas and validation models
│   │   ├── services/              # Domain logic (ETA, Smart Engine, Context, Assistant, AI)
│   │   └── worker/                # Celery application, tasks, and beat schedules
│   ├── migrations/                # Alembic migration revisions
│   └── tests/                     # 128+ automated unit, integration, and load tests
├── frontend/
│   ├── Dockerfile                 # Multi-stage production container (Node 20 -> Alpine Nginx)
│   ├── nginx.conf                 # Production Nginx config (SPA routing, Gzip, Security headers)
│   ├── package.json               # Frontend dependencies (React 19, Vite, Tailwind CSS, Lucide)
│   ├── .env.example               # Frontend environment reference
│   └── src/                       # Components, Pages, Stores (Zustand), Themes, API clients
├── docker-compose.yml             # Local development compose (Hot reloading enabled)
├── docker-compose.prod.yml        # Hardened production compose (Isolated internal networks)
├── DEPLOYMENT.md                  # Comprehensive staging and production deployment runbook
├── OPERATIONS.md                  # SRE operations guide, metrics, and incident runbooks
├── SECURITY.md                    # Defensive security policy and threat mitigation model
├── BACKUP_AND_RESTORE.md          # PostgreSQL backup automation & disaster recovery runbook
├── .gitignore                     # Production Git ignore rules
└── README.md                      # Project documentation
```

---

## 🚀 Quickstart & Local Development

### Option A: Using Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/buildwithneel/ADA-Smart-Alarm.git
   cd ADA-Smart-Alarm
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Google Maps, Firebase, or AI API keys (optional for local mock mode)
   ```

3. **Launch all services:**
   ```bash
   docker compose up --build
   ```

4. **Access endpoints:**
   * **Web Frontend:** [http://localhost:5173](http://localhost:5173)
   * **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   * **Health Check:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
   * **Prometheus Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)

---

### Option B: Manual Local Setup

#### 1. Backend Setup:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start Celery Worker & Beat (Separate Terminals):
```bash
# Terminal 2: Worker
celery -A app.worker.celery_app.celery worker --loglevel=info

# Terminal 3: Beat Scheduler
celery -A app.worker.celery_app.celery beat --loglevel=info
```

#### 3. Frontend Setup:
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Verification

ADA maintains comprehensive test coverage across all domain calculation engines, security rules, and user interfaces.

### Backend Test Suite (128 Tests):
```bash
cd backend
pytest -v
```

### Frontend Vitest Suite (29 Tests):
```bash
cd frontend
npm test
```

### Frontend Production Build:
```bash
cd frontend
npm run build
```

### Standalone Production Load & Resilience Benchmark:
```bash
cd backend
python tests/load_test.py
```

*Benchmark Results (Local Baseline):*
* **Concurrent Health Probes:** `517.2 req/s` (Median latency: `19.4ms`)
* **Prometheus Telemetry Scrapes:** `895.0 req/s` (Median latency: `9.5ms`)
* **Oversized Payload DOS Defense:** Rejects 3MB payload with `HTTP 413` in `< 2ms`
* **Defensive HTTP Headers:** `100% PASS`

---

## 🌐 Production Deployment

For deploying to staging or production Kubernetes, AWS ECS, GCP Cloud Run, or Docker Compose:

1. Follow the **[Production Deployment Guide (DEPLOYMENT.md)](DEPLOYMENT.md)**.
2. Review the **[SRE Operations & Incident Runbook (OPERATIONS.md)](OPERATIONS.md)**.
3. Review the **[Security Policy & Architecture (SECURITY.md)](SECURITY.md)**.
4. Set up automated backups using **[Database Backup & Disaster Recovery (BACKUP_AND_RESTORE.md)](BACKUP_AND_RESTORE.md)**.

### Quick Production Launch via Docker Compose:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 📄 License & Attribution

Developed with ❤️ by [Neel Agrawal](https://github.com/buildwithneel) as an open, resilient smart alarm platform.

Licensed under the [MIT License](LICENSE).
