import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.database import SessionLocal
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.services.alarm_recalculation_service import AlarmRecalculationService
from app.services.alarm_service import AlarmService
from app.worker.celery_app import celery

logger = logging.getLogger("ada.worker")


@celery.task(name="app.worker.tasks.health_ping")
def health_ping() -> dict:
    """
    Diagnostic Celery worker test task to verify broker and task worker functionality.
    """
    logger.info("Executing Celery worker health_ping task.")
    return {
        "status": "ok",
        "task": "health_ping",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery.task(name="app.worker.tasks.refresh_alarm_eta")
def refresh_alarm_eta(alarm_id: str, expected_version: Optional[int] = None) -> dict:
    """
    Background worker task to re-evaluate ETA and schedule for a specific alarm.
    Delegates to AlarmRecalculationService with distributed locking & optimistic concurrency checks.
    """
    logger.info(f"Celery task: refresh_alarm_eta for {alarm_id} (expected_version={expected_version})")
    db = SessionLocal()
    try:
        alarm_repo = AlarmRepository(db)
        dest_repo = DestinationRepository(db)
        recalc_service = AlarmRecalculationService(alarm_repo, dest_repo)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            recalc_service.recalculate_alarm(
                alarm_id=uuid.UUID(alarm_id),
                expected_version=expected_version,
            )
        )
        loop.close()

        return {
            "status": result.status,
            "alarm_id": alarm_id,
            "schedule_changed": result.schedule_changed,
            "schedule_version": result.schedule_version,
            "reason": result.change_reason,
            "wake_time": result.new_wake_time.isoformat() if result.new_wake_time else None,
            "leave_time": result.new_leave_time.isoformat() if result.new_leave_time else None,
            "travel_minutes": result.new_travel_minutes,
            "route_freshness": result.route_freshness,
        }
    except Exception as exc:
        logger.error(f"Error in refresh_alarm_eta task for {alarm_id}: {exc}", exc_info=True)
        return {"status": "error", "alarm_id": alarm_id, "error": str(exc)}
    finally:
        db.close()


@celery.task(name="app.worker.tasks.refresh_upcoming_alarms")
def refresh_upcoming_alarms() -> dict:
    """
    Celery Beat background task for Step 8:
    Batch-evaluates all active upcoming alarms within the UPCOMING_ALARM_WINDOW_SECONDS window,
    requests real-time traffic-aware routes, detects meaningful changes, and recalculates schedules.
    """
    logger.info("Executing Celery periodic task: refresh_upcoming_alarms")
    db = SessionLocal()
    try:
        alarm_repo = AlarmRepository(db)
        dest_repo = DestinationRepository(db)
        recalc_service = AlarmRecalculationService(alarm_repo, dest_repo)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(
            recalc_service.refresh_all_upcoming_alarms()
        )
        loop.close()

        return {
            "status": "success",
            "evaluated_count": stats.get("evaluated", 0),
            "updated_count": stats.get("updated", 0),
            "unchanged_count": stats.get("unchanged", 0),
            "skipped_count": stats.get("skipped", 0),
            "error_count": stats.get("errors", 0),
            "stats": stats,
        }
    except Exception as exc:
        logger.error(f"Error in refresh_upcoming_alarms task: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery.task(name="app.worker.tasks.check_expired_alarms")
def check_expired_alarms() -> dict:
    """
    Background maintenance task to mark past one-time alarms as EXPIRED.
    """
    logger.info("Celery task: check_expired_alarms starting")
    db = SessionLocal()
    try:
        alarm_repo = AlarmRepository(db)
        dest_repo = DestinationRepository(db)
        alarm_service = AlarmService(alarm_repo, dest_repo)
        count = alarm_service.mark_expired_alarms()
        return {"status": "success", "expired_count": count}
    finally:
        db.close()


@celery.task(name="app.worker.tasks.deliver_due_notifications")
def deliver_due_notifications() -> dict:
    """
    Step 9 Celery Beat periodic task:
    Evaluates all due notifications (scheduled_for <= now and status == PENDING),
    validates alarm and version freshness, and delivers across enabled channels.
    """
    logger.info("Executing Celery periodic task: deliver_due_notifications")
    db = SessionLocal()
    try:
        from app.repositories.notification_repository import NotificationRepository
        from app.repositories.preference_repository import PreferenceRepository
        from app.repositories.push_subscription_repository import PushSubscriptionRepository
        from app.services.notification_service import NotificationService

        notif_repo = NotificationRepository(db)
        push_repo = PushSubscriptionRepository(db)
        alarm_repo = AlarmRepository(db)
        pref_repo = PreferenceRepository(db)
        notif_service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(
            notif_service.process_due_notifications(current_time=datetime.now(timezone.utc))
        )
        loop.close()

        return {
            "status": "success",
            "evaluated": stats.get("evaluated", 0),
            "delivered": stats.get("delivered", 0),
            "failed": stats.get("failed", 0),
            "skipped": stats.get("skipped", 0),
        }
    except Exception as exc:
        logger.error(f"Error in deliver_due_notifications task: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery.task(
    name="app.worker.tasks.deliver_single_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_single_notification(self, notification_id: str) -> dict:
    """
    Delivers a single notification with automatic retry on transient failures.
    """
    logger.info(f"Executing Celery task: deliver_single_notification ({notification_id})")
    db = SessionLocal()
    try:
        from app.repositories.notification_repository import NotificationRepository
        from app.repositories.preference_repository import PreferenceRepository
        from app.repositories.push_subscription_repository import PushSubscriptionRepository
        from app.services.notification_service import NotificationService

        notif_repo = NotificationRepository(db)
        push_repo = PushSubscriptionRepository(db)
        alarm_repo = AlarmRepository(db)
        pref_repo = PreferenceRepository(db)
        notif_service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            notif_service.deliver_notification(uuid.UUID(notification_id))
        )
        loop.close()

        if not result.success and result.is_transient:
            logger.warning(
                f"Transient error delivering notification {notification_id}: {result.error_message}. Retrying..."
            )
            raise self.retry(exc=Exception(result.error_message))

        return {
            "status": "success" if result.success else "failure",
            "provider": result.provider_name,
            "error": result.error_message,
        }
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                f"deliver_single_notification for {notification_id} exceeded max retries: {exc}"
            )
            return {"status": "failed", "error": str(exc)}
        raise
    finally:
        db.close()


@celery.task(name="app.worker.tasks.sync_active_calendars")
def sync_active_calendars() -> dict:
    """
    Step 10 Celery Beat periodic task:
    Synchronizes upcoming calendar events for all active user connections.
    """
    logger.info("Executing Celery periodic task: sync_active_calendars")
    db = SessionLocal()
    try:
        from app.repositories.calendar_repository import CalendarRepository
        from app.repositories.preference_repository import PreferenceRepository
        from app.services.calendar.calendar_service import CalendarService

        cal_repo = CalendarRepository(db)
        alarm_repo = AlarmRepository(db)
        dest_repo = DestinationRepository(db)
        pref_repo = PreferenceRepository(db)
        cal_service = CalendarService(
            calendar_repo=cal_repo,
            alarm_repo=alarm_repo,
            destination_repo=dest_repo,
            pref_repo=pref_repo,
        )

        connections = cal_repo.list_all_active_connections()
        success_count = 0
        failed_count = 0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for conn in connections:
            try:
                res = loop.run_until_complete(cal_service.sync_connection_events(conn.id))
                if res.get("status") == "success":
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                logger.error(f"Error syncing connection {conn.id}: {exc}")
                failed_count += 1
        loop.close()

        return {
            "status": "success",
            "total_connections": len(connections),
            "synced": success_count,
            "failed": failed_count,
        }
    except Exception as exc:
        logger.error(f"Error in sync_active_calendars task: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery.task(name="app.worker.tasks.evaluate_upcoming_weather_context")
def evaluate_upcoming_weather_context() -> dict:
    """
    Step 10 Celery Beat periodic task:
    Sweeps active upcoming alarms within the upcoming window and evaluates
    weather context against configured user buffer policies.
    """
    logger.info("Executing Celery periodic task: evaluate_upcoming_weather_context")
    db = SessionLocal()
    try:
        from datetime import timedelta
        from app.repositories.calendar_repository import CalendarRepository
        from app.repositories.preference_repository import PreferenceRepository
        from app.services.context.context_service import ContextAction, ContextFinding, ContextService

        alarm_repo = AlarmRepository(db)
        dest_repo = DestinationRepository(db)
        pref_repo = PreferenceRepository(db)
        cal_repo = CalendarRepository(db)
        context_svc = ContextService(
            alarm_repo=alarm_repo,
            destination_repo=dest_repo,
            pref_repo=pref_repo,
            calendar_repo=cal_repo,
        )

        now = datetime.now(timezone.utc)
        window = now + timedelta(seconds=settings.UPCOMING_ALARM_WINDOW_SECONDS)
        alarms = alarm_repo.get_upcoming_alarms(window_end=window)

        evaluated = 0
        buffers_applied = 0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for alarm in alarms:
            try:
                results = loop.run_until_complete(
                    context_svc.evaluate_alarm_context(alarm.id, alarm.user_id)
                )
                evaluated += 1

                for r in results:
                    if (
                        r.recommended_action == ContextAction.APPLY_BUFFER
                        and not r.requires_confirmation
                    ):
                        recalc_res = loop.run_until_complete(
                            context_svc.apply_weather_buffer(
                                alarm_id=alarm.id,
                                user_id=alarm.user_id,
                                buffer_minutes=r.recommended_buffer_minutes,
                                expected_version=alarm.schedule_version,
                            )
                        )
                        if recalc_res.schedule_changed:
                            buffers_applied += 1
            except Exception as exc:
                logger.warning(f"Error evaluating context for alarm {alarm.id}: {exc}")
        loop.close()

        return {
            "status": "success",
            "evaluated_alarms": evaluated,
            "buffers_applied": buffers_applied,
        }
    except Exception as exc:
        logger.error(f"Error in evaluate_upcoming_weather_context: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


@celery.task(name="app.worker.tasks.reconcile_missed_alarms")
def reconcile_missed_alarms() -> dict:
    """
    Step 12 Production Resilience Task:
    1. Sweeps through alarms to detect one-time active alarms whose target arrival has passed
       (e.g., during worker outage or downtime) and reconciles them to COMPLETED.
    2. Sweeps through notifications stuck in PENDING status whose scheduled delivery window
       passed more than 30 minutes ago, marking them as SUPERSEDED so stale alerts never ring late.
    """
    logger.info("Executing Celery periodic task: reconcile_missed_alarms")
    db = SessionLocal()
    try:
        from datetime import timedelta
        from app.models.alarm import Alarm, AlarmStatus
        from app.models.notification import Notification, NotificationStatus

        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(minutes=30)

        # 1. Reconcile past one-time alarms
        past_active_alarms = (
            db.query(Alarm)
            .filter(
                Alarm.is_recurring.is_(False),
                Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.SCHEDULED]),
                Alarm.target_arrival_time < now,
            )
            .all()
        )
        alarms_reconciled = 0
        for alarm in past_active_alarms:
            alarm.status = AlarmStatus.COMPLETED
            alarm.is_active = False
            alarms_reconciled += 1

        # 2. Cancel stale pending notifications (avoid waking user hours late after downtime)
        stale_notifications = (
            db.query(Notification)
            .filter(
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_for < stale_cutoff,
            )
            .all()
        )
        notifications_reconciled = 0
        for notif in stale_notifications:
            notif.status = NotificationStatus.SUPERSEDED
            notif.error_message = "Delivery window expired during worker downtime or delay."
            notifications_reconciled += 1

        if alarms_reconciled > 0 or notifications_reconciled > 0:
            db.commit()
            logger.info(
                f"Reconciliation completed: {alarms_reconciled} alarms updated, "
                f"{notifications_reconciled} stale notifications superseded."
            )

        return {
            "status": "success",
            "alarms_reconciled": alarms_reconciled,
            "notifications_reconciled": notifications_reconciled,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Error in reconcile_missed_alarms task: {exc}", exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()

