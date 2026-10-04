from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Initialize Celery app instance
celery = Celery(
    "ada_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

# Core configurations - Production Hardened
celery.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,  # Requeue task if worker process is abruptly killed/dies
    task_time_limit=120,              # Hard timeout 120 seconds per task
    task_soft_time_limit=90,          # Soft timeout 90 seconds (allows cleanup/graceful exit)
    result_expires=3600,              # Redis result backend expiry 1 hour (prevents memory leaks)
    broker_connection_retry_on_startup=True,
)

# Periodic scheduler structure (Celery Beat)
celery.conf.beat_schedule = {
    "celery-worker-health-ping": {
        "task": "app.worker.tasks.health_ping",
        "schedule": crontab(minute="*/5"),  # Diagnostic heartbeat every 5 minutes
    },
    "refresh-upcoming-alarms": {
        "task": "app.worker.tasks.refresh_upcoming_alarms",
        "schedule": float(settings.TRAFFIC_REFRESH_INTERVAL_SECONDS),  # Periodic traffic-aware evaluation
    },
    "check-expired-alarms": {
        "task": "app.worker.tasks.check_expired_alarms",
        "schedule": crontab(minute="*/15"),  # Clean up past one-time alarms every 15 minutes
    },
    "deliver-due-notifications": {
        "task": "app.worker.tasks.deliver_due_notifications",
        "schedule": float(settings.NOTIFICATION_SWEEP_INTERVAL_SECONDS),  # Sweep every 30 seconds
    },
    # Step 10: Weather + Calendar Periodic Tasks
    "sync-active-calendars": {
        "task": "app.worker.tasks.sync_active_calendars",
        "schedule": float(settings.CALENDAR_SYNC_INTERVAL_SECONDS),  # Periodic calendar sync every 15 min
    },
    "evaluate-upcoming-weather-context": {
        "task": "app.worker.tasks.evaluate_upcoming_weather_context",
        "schedule": float(settings.WEATHER_SWEEP_INTERVAL_SECONDS),  # Periodic weather evaluation every 10 min
    },
    # Step 12: Production Reliability - Outage and Downtime Reconciliation
    "reconcile-missed-alarms": {
        "task": "app.worker.tasks.reconcile_missed_alarms",
        "schedule": crontab(minute="*/10"),  # Reconcile missed alarms and stale pending alerts every 10 min
    },
}


