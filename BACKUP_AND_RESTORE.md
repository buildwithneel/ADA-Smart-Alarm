# ADA Database Backup & Disaster Recovery Runbook

This runbook outlines the backup, restoration, and disaster recovery procedures for the ADA platform's persistent PostgreSQL database and Redis state.

---

## 1. Disaster Recovery Objectives

- **Recovery Point Objective (RPO):** < 1 hour (for scheduled logical dumps); < 5 minutes (when using PostgreSQL WAL streaming or Cloud RDS automated backups).
- **Recovery Time Objective (RTO):** < 30 minutes to restore service on replacement infrastructure.

---

## 2. PostgreSQL Backup Procedures

### Automated Daily Logical Dump (`pg_dump`)
Run this backup script via a dedicated cron job or container:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/ada/postgres"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/ada_prod_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting PostgreSQL backup to ${BACKUP_FILE}..."

# Export compressed database archive using custom format
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${POSTGRES_SERVER:-localhost}" \
  -U "${POSTGRES_USER:-ada_admin}" \
  -d "${POSTGRES_DB:-ada_prod}" \
  -F c -b -v \
  | gzip -c > "${BACKUP_FILE}"

echo "[$(date)] Backup completed successfully. Size: $(du -h "${BACKUP_FILE}" | cut -f1)"

# Encrypt backup archive with GPG (AES-256)
gpg --symmetric --cipher-algo AES256 --batch --passphrase "${BACKUP_ENCRYPTION_KEY}" "${BACKUP_FILE}"
rm -f "${BACKUP_FILE}"

# Retain backups for 30 days locally, purge older archives
find "${BACKUP_DIR}" -name "ada_prod_*.sql.gz.gpg" -mtime +30 -delete

echo "[$(date)] Backup encrypted and retention enforced."
```

---

## 3. Database Restoration Runbook

> **Critical Safety Rule:** Never test or execute a restoration against the live production database instance. Always restore into an isolated staging or recovery environment.

### Step 1: Prepare Isolated Recovery Database
```bash
# Launch a disposable container or target staging instance
docker run -d --name ada_recovery_db \
  -e POSTGRES_DB=ada_recovery \
  -e POSTGRES_USER=ada_admin \
  -e POSTGRES_PASSWORD=recovery_pass \
  postgres:15-alpine
```

### Step 2: Decrypt and Decompress the Backup Archive
```bash
# Decrypt GPG archive
gpg --decrypt --batch --passphrase "${BACKUP_ENCRYPTION_KEY}" \
  /var/backups/ada/postgres/ada_prod_20261004_120000Z.sql.gz.gpg > /tmp/restore_target.sql.gz

# Decompress
gunzip /tmp/restore_target.sql.gz
```

### Step 3: Execute Database Restore
```bash
PGPASSWORD="recovery_pass" pg_restore \
  -h localhost -p 5432 \
  -U ada_admin \
  -d ada_recovery \
  -v --clean --if-exists /tmp/restore_target.sql
```

### Step 4: Verify Schema and Migration State
Verify that all Alembic migrations are recognized in the restored database:
```bash
export DATABASE_URL="postgresql://ada_admin:recovery_pass@localhost:5432/ada_recovery"
cd backend
alembic current
alembic check
```

### Step 5: Clean Up Decrypted Artifacts
```bash
shred -u /tmp/restore_target.sql
```

---

## 4. Redis Recovery & State Durability

### Durable State vs Ephemeral State
- **Authoritative Data:** Alarms, user profiles, travel preferences, and schedule changes are stored **strictly in PostgreSQL**.
- **Ephemeral State:** Redis stores Celery task queues, distributed locks, routing cache, and geocoding cache.
- In production, Redis is configured with `--appendonly yes` (AOF) in `docker-compose.prod.yml` to preserve pending task queues across container restarts.

### Recovery After Redis Loss
If Redis suffers total catastrophic memory loss:
1. Re-launch Redis container (`docker compose -f docker-compose.prod.yml up -d redis`).
2. Celery workers will automatically reconnect (`broker_connection_retry_on_startup=True`).
3. The Celery Beat periodic task `refresh-upcoming-alarms` will immediately sweep active alarms from PostgreSQL within the 4-hour window and re-queue necessary recalculations.
4. The `reconcile_missed_alarms` task will identify any past-due alarms and mark them as COMPLETED. No alarm records are lost.
