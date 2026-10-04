# ADA Production Deployment Guide

This guide describes how to deploy the ADA (Adaptive Dynamic Alarm) platform to staging and production environments.

---

## 1. System Requirements & Architecture

| Component | Technology | Minimum Specification |
|---|---|---|
| **API Backend** | Python 3.11 / FastAPI / Uvicorn | 2 vCPU, 2 GB RAM |
| **Worker Engine** | Celery 5.3+ (Prefetch=1, Acks Late) | 2 vCPU, 2 GB RAM |
| **Scheduler** | Celery Beat (Singleton) | 0.5 vCPU, 512 MB RAM |
| **Relational Database** | PostgreSQL 15+ | 2 vCPU, 4 GB RAM, SSD (AWS RDS / Supabase / Neon) |
| **Distributed Broker / Cache** | Redis 7+ (AOF enabled) | 1 vCPU, 1 GB RAM (Redis Cloud / AWS ElastiCache) |
| **Frontend Web App** | React 19 + TypeScript + Vite | Static CDN (Cloudflare Pages / Vercel / Nginx) |

---

## 2. Environment Configuration

Copy the production template and populate all required secrets:

```bash
cp .env.example .env.production
```

### Critical Production Variables Checklist:
- `ENVIRONMENT=production`
- `SECRET_KEY`: Minimum 32-character cryptographically secure string (generated via `openssl rand -hex 32`).
- `DATABASE_URL`: Production PostgreSQL connection string with SSL (`sslmode=require`).
- `POSTGRES_PASSWORD`: Must be changed from the default development value.
- `REDIS_URL` & `CELERY_BROKER_URL`: Authenticated Redis connection with password.
- `CORS_ORIGINS`: Comma-separated list of trusted production frontend domains (e.g. `https://ada-alarm.app`).
- `ENABLE_DOCS=false`: Disables public Swagger/ReDoc endpoints in production.
- `JSON_LOGGING=true`: Enables structured RFC 8259 JSON output for log aggregators.
- `FIREBASE_PROJECT_ID`: Production Firebase Project ID for token signature verification.
- `ROUTING_PROVIDER` & `GEOCODING_PROVIDER`: `google` or `mapbox`.
- `GOOGLE_MAPS_API_KEY` / `MAPBOX_ACCESS_TOKEN`: Production keys with IP and HTTP referrer restrictions.

---

## 3. Database Migration Procedure

Alembic migrations must be executed **before** newly deployed application containers begin serving live traffic.

### Running Migrations Manually:
```bash
cd backend
alembic upgrade head
```

### Inspecting Current Migration Revision:
```bash
alembic current
```

### Rolling Back One Migration (If Needed):
```bash
alembic downgrade -1
```

> **Warning:** Never enable auto-running destructive migrations on multiple web worker boot loops. In containerized environments, use the dedicated one-shot `db_migrate` service provided in `docker-compose.prod.yml` or a Kubernetes pre-install Job.

---

## 4. Production Deployment via Docker Compose

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/thinkx/Alarm.git /opt/ada
cd /opt/ada
cp .env.example .env
chmod 600 .env
# Edit .env with production credentials
nano .env
```

### Step 2: Build & Launch Services
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Step 3: Verify Startup & Health Probes
```bash
# Verify all containers are healthy
docker compose -f docker-compose.prod.yml ps

# Check API Liveness Probe
curl -f http://localhost:8000/health/live

# Check API Readiness Probe (Verifies PostgreSQL & Redis connections)
curl -f http://localhost:8000/health/ready

# Check Prometheus Telemetry
curl -s http://localhost:8000/metrics
```

---

## 5. Alternative Cloud Deployments

### Backend (AWS ECS / GCP Cloud Run / Render / Railway)
- **Container image:** Build using `backend/Dockerfile` (runs as non-root user `ada`).
- **Healthcheck Path:** `/health/live` (port 8000).
- **Readiness Path:** `/health/ready` (port 8000).
- **Scale:** Minimum 2 instances behind Application Load Balancer.

### Celery Workers & Beat
- **Worker Command:** `celery -A app.worker.celery_app.celery worker --loglevel=info --concurrency=4`
- **Beat Command:** `celery -A app.worker.celery_app.celery beat --loglevel=info`
- **Important:** Celery Beat MUST run as a singleton (exactly 1 instance). Running multiple Beat schedulers will generate duplicate alarm sweeps.

### Frontend (Cloudflare Pages / Vercel / Netlify / AWS S3 + CloudFront)
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variables:** `VITE_API_BASE_URL`, `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_PROJECT_ID`, `VITE_VAPID_PUBLIC_KEY`.
- **SPA Rewrite Rule:** Route all requests (`/*`) to `/index.html`.

---

## 6. Zero-Downtime Rolling Update & Rollback

### Rolling Update:
```bash
# 1. Pull latest verified release
git pull origin main

# 2. Run new database migrations
docker compose -f docker-compose.prod.yml run --rm db_migrate alembic upgrade head

# 3. Build updated images
docker compose -f docker-compose.prod.yml build api celery_worker frontend

# 4. Graceful container restart
docker compose -f docker-compose.prod.yml up -d --no-deps api celery_worker frontend
```

### Emergency Rollback:
```bash
# 1. Checkout previous stable commit
git checkout <PREVIOUS_COMMIT_TAG>

# 2. Roll back migration if backward-incompatible schema change was introduced
docker compose -f docker-compose.prod.yml run --rm db_migrate alembic downgrade -1

# 3. Rebuild and restart containers
docker compose -f docker-compose.prod.yml up -d --build
```
