# ADA Operations & SRE Runbook

This runbook provides site reliability engineers and operators with procedures for monitoring, diagnosing, and resolving incidents across the ADA platform.

---

## 1. Observability Architecture

### Structured JSON Logging
When `JSON_LOGGING=true` (default in production), the application emits RFC 8259 compliant single-line JSON logs to standard output:

```json
{
  "timestamp": "2026-10-04T12:00:00Z",
  "level": "INFO",
  "service": "ada-backend",
  "environment": "production",
  "logger": "ada.access",
  "message": "method=POST path=/api/v1/eta/calculate status=200 latency=0.0450s request_id=6f8d39e2-12a4-4c8d-9ef2-1b1d44c9b910",
  "request_id": "6f8d39e2-12a4-4c8d-9ef2-1b1d44c9b910"
}
```

#### Sensitive Data Redaction
The logger automatically intercepts and sanitizes:
- Authorization headers (`Bearer [REDACTED]`)
- API keys, OAuth tokens, and passwords in log arguments
- Precise destination addresses in telemetry metric labels

---

## 2. Health Endpoints & Probes

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/health/live` | `GET` | Process liveness probe | `200 OK {"status": "alive"}` |
| `/health/ready` | `GET` | Dependency readiness probe | `200 OK {"status": "ready"}` or `503 Unavailable` |
| `/health/deps` | `GET` | Diagnostic latency breakdown | `200 OK` with latency per service (Postgres, Redis, Maps, AI) |
| `/metrics` | `GET` | Prometheus telemetry scrape | Standard Prometheus format or JSON (`?format=json`) |

---

## 3. Key Operational Metrics & Alerts

| Metric Name | Type | Warning Threshold | Critical Action |
|---|---|---|---|
| `ada_db_pool_checked_out` | Gauge | `> 80%` of pool size for 2m | Investigate long-running queries or connection leak. |
| `ada_db_pool_overflow` | Gauge | `> 10` for 1m | Increase `DB_POOL_SIZE` or tune query concurrency. |
| `ada_uptime_seconds` | Counter | Decreasing | Unexpected container restarts / OOM kills. |
| `celery_task_failures` | Counter | `> 5%` failure rate | Check third-party provider status (Google Maps / VAPID). |
| `http_requests_5xx` | Counter | `> 1%` over 5m | Check application error logs filtering by `level: ERROR`. |

---

## 4. Incident Response Runbooks

### Runbook 1: PostgreSQL Connection Pool Saturation
**Symptom:** API requests fail with `TimeoutError: QueuePool limit of size 15 overflow 25 reached, connection timed out`.

**Immediate Steps:**
1. Check active database connections:
   ```sql
   SELECT pid, state, age(clock_timestamp(), query_start), query 
   FROM pg_stat_activity 
   WHERE state != 'idle' 
   ORDER BY query_start ASC;
   ```
2. Terminate rogue / blocked queries:
   ```sql
   SELECT pg_terminate_backend(<PID>);
   ```
3. Adjust pool configuration in `.env` if legitimate workload has scaled:
   ```env
   DB_POOL_SIZE=30
   DB_MAX_OVERFLOW=50
   DB_POOL_TIMEOUT=45
   ```
4. Restart API containers:
   ```bash
   docker compose -f docker-compose.prod.yml restart api
   ```

---

### Runbook 2: Redis Outage or Worker Queue Backlog
**Symptom:** Alarms are not recalculating; notifications are delayed; `/health/ready` reports `503`.

**Immediate Steps:**
1. Check Redis process status:
   ```bash
   docker compose -f docker-compose.prod.yml exec redis redis-cli ping
   ```
2. Inspect Celery queue backlog:
   ```bash
   docker compose -f docker-compose.prod.yml exec celery_worker celery -A app.worker.celery_app.celery inspect active
   docker compose -f docker-compose.prod.yml exec celery_worker celery -A app.worker.celery_app.celery inspect reserved
   ```
3. Restart Redis and Worker processes:
   ```bash
   docker compose -f docker-compose.prod.yml restart redis celery_worker
   ```
4. Verify the `reconcile_missed_alarms` periodic task marks past elapsed tasks cleanly rather than firing late notifications.

---

### Runbook 3: Missed Alarm Investigation
**Symptom:** A user reports an alarm did not sound or calculate their departure time.

**Diagnostic Steps:**
1. Locate the alarm ID and user ID in the database:
   ```sql
   SELECT id, title, target_arrival_time, calculated_leave_time, calculated_wake_time, status, schedule_version 
   FROM alarms 
   WHERE user_id = '<USER_UUID>' 
   ORDER BY created_at DESC LIMIT 5;
   ```
2. Trace schedule changes for the alarm:
   ```sql
   SELECT previous_wake_time, new_wake_time, change_reason, created_at 
   FROM alarm_schedule_changes 
   WHERE alarm_id = '<ALARM_UUID>' 
   ORDER BY created_at DESC;
   ```
3. Check notification delivery attempts:
   ```sql
   SELECT id, notification_type, channel, status, retry_count, error_message, sent_at 
   FROM notifications 
   WHERE alarm_id = '<ALARM_UUID>';
   ```
4. If browser push delivery failed with `410 Gone` or `InvalidSubscription`:
   - The user uninstalled the PWA or revoked browser notification permissions.
   - The subscription has been marked inactive. Instruct the user to re-enable notifications in Settings.

---

### Runbook 4: Routing Provider Quota Exceeded / Fallback
**Symptom:** Real-time traffic recalculations fail with `OVER_QUERY_LIMIT` or `429 Too Many Requests`.

**Remediation:**
1. The system automatically falls back from Google Maps to Mapbox if `ENABLE_PROVIDER_FALLBACK=true`.
2. Inspect fallback logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs api | grep "Provider fallback"
   ```
3. If primary key quota is exhausted, switch primary provider in `.env`:
   ```env
   ROUTING_PROVIDER=mapbox
   ROUTING_FALLBACK_PROVIDER=google
   ```
4. Apply changes without downtime:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps api celery_worker
   ```
