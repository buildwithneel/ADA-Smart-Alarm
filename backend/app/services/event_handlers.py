from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

import app.core.database
from app.core.events import AlarmEvent, AlarmEventType, register_alarm_event_listener
from app.models.alarm import AlarmStatus
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger("ada.events.handlers")


def handle_alarm_domain_event(event: AlarmEvent, db_session: Optional[Session] = None) -> None:
    """
    Decoupled domain event listener that handles alarm state changes
    and schedules or updates notifications accordingly.
    """
    should_close = False
    db = db_session
    if db is None:
        db = app.core.database.SessionLocal()
        should_close = True

    try:
        alarm_repo = AlarmRepository(db)
        notif_repo = NotificationRepository(db)
        push_repo = PushSubscriptionRepository(db)
        pref_repo = PreferenceRepository(db)
        notif_service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)

        alarm_id = uuid.UUID(event.alarm_id)

        if event.event_type == AlarmEventType.ALARM_SCHEDULED:
            alarm = alarm_repo.get(alarm_id)
            if alarm and alarm.status == AlarmStatus.ACTIVE:
                notif_service.schedule_alarm_notifications(alarm)

        elif event.event_type in (AlarmEventType.ALARM_RECALCULATED, AlarmEventType.ALARM_URGENT_CHANGE):
            alarm = alarm_repo.get(alarm_id)
            if alarm:
                prev_wake_str = event.payload.get("previous_wake_time")
                prev_wake = datetime.fromisoformat(prev_wake_str) if prev_wake_str else None

                new_wake_str = event.payload.get("new_wake_time")
                new_wake = datetime.fromisoformat(new_wake_str) if new_wake_str else (alarm.wake_time or datetime.utcnow())

                change_reason = event.payload.get("reason", "traffic recalculation")
                is_urgent = (event.event_type == AlarmEventType.ALARM_URGENT_CHANGE)

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        notif_service.handle_schedule_changed(
                            alarm=alarm,
                            previous_wake=prev_wake,
                            new_wake=new_wake,
                            change_reason=change_reason,
                            is_urgent=is_urgent,
                        )
                    )
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        notif_service.handle_schedule_changed(
                            alarm=alarm,
                            previous_wake=prev_wake,
                            new_wake=new_wake,
                            change_reason=change_reason,
                            is_urgent=is_urgent,
                        )
                    )
                    loop.close()

        elif event.event_type in (
            AlarmEventType.ALARM_DISABLED,
            AlarmEventType.ALARM_CANCELLED,
            AlarmEventType.ALARM_EXPIRED,
            AlarmEventType.ALARM_COMPLETED,
        ):
            notif_service.handle_alarm_disabled_or_cancelled(
                alarm_id=alarm_id, reason=f"Domain event {event.event_type.value}"
            )

    except Exception as exc:
        logger.error(
            f"Error processing domain event {event.event_type.value} for alarm {event.alarm_id}: {exc}",
            exc_info=True,
        )
    finally:
        if should_close:
            db.close()


def init_domain_event_subscribers() -> None:
    """Registers domain event subscribers on application startup."""
    register_alarm_event_listener(handle_alarm_domain_event)
    logger.info("Initialized domain event subscribers for NotificationService.")
