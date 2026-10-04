from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alarm import Alarm, AlarmStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.preference import UserPreference
from app.models.push_subscription import PushSubscription
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.schemas.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationTestRequest,
)
from app.services.delivery.base import DeliveryResult, NotificationDeliveryProvider
from app.services.delivery.composite_provider import CompositeNotificationProvider
from app.services.delivery.in_app_provider import InAppNotificationProvider
from app.services.delivery.web_push_provider import WebPushNotificationProvider

logger = logging.getLogger("ada.services.notification")

_MEMORY_LOCKS: dict[str, threading.Lock] = {}
_MEMORY_LOCKS_MUTEX = threading.Lock()


def _ensure_tz(dt: Optional[datetime], default_tz: ZoneInfo = ZoneInfo("UTC")) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt


class NotificationService:
    """
    Core notification and alarm delivery service.
    Orchestrates due event evaluation, idempotency, schedule version validation,
    and dispatch across In-App and Web Push channels.
    """

    def __init__(
        self,
        notification_repo: NotificationRepository,
        push_repo: PushSubscriptionRepository,
        alarm_repo: AlarmRepository,
        preference_repo: PreferenceRepository,
        delivery_provider: Optional[NotificationDeliveryProvider] = None,
        redis_client: Optional[redis.Redis] = None,
    ):
        self.notification_repo = notification_repo
        self.push_repo = push_repo
        self.alarm_repo = alarm_repo
        self.preference_repo = preference_repo
        self.redis_client = redis_client

        if delivery_provider:
            self.delivery_provider = delivery_provider
        else:
            in_app = InAppNotificationProvider()
            web_push = WebPushNotificationProvider(self.push_repo)
            self.delivery_provider = CompositeNotificationProvider([in_app, web_push])

        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL, decode_responses=True, socket_timeout=1.0
                )
                self.redis_client.ping()
            except Exception:
                self.redis_client = None

    def _acquire_lock(self, key: str, timeout: int = 20) -> bool:
        if self.redis_client:
            try:
                return bool(self.redis_client.set(key, "1", nx=True, ex=timeout))
            except Exception as e:
                logger.warning(f"Redis lock failed for {key}: {e}. Falling back to memory lock.")
        with _MEMORY_LOCKS_MUTEX:
            if key not in _MEMORY_LOCKS:
                _MEMORY_LOCKS[key] = threading.Lock()
            return _MEMORY_LOCKS[key].acquire(blocking=False)

    def _release_lock(self, key: str) -> None:
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return
            except Exception as e:
                logger.warning(f"Failed to release Redis lock for {key}: {e}")
        with _MEMORY_LOCKS_MUTEX:
            lock = _MEMORY_LOCKS.get(key)
            if lock and lock.locked():
                try:
                    lock.release()
                except RuntimeError:
                    pass

    # -------------------------------------------------------------------------
    # Notification Scheduling & Lifecycle
    # -------------------------------------------------------------------------

    def schedule_alarm_notifications(
        self, alarm: Alarm, user_pref: Optional[UserPreference] = None
    ) -> List[Notification]:
        """
        Schedules wake alarm and departure reminder events for an active alarm.
        Tags records with the alarm's current schedule_version.
        """
        if not user_pref:
            user_pref = self.preference_repo.get_by_user(alarm.user_id)

        dest_name = alarm.destination.name if alarm.destination else "Destination"
        created: List[Notification] = []

        # 1. Primary Wake Alarm Event
        if alarm.wake_time:
            wake_dt = _ensure_tz(alarm.wake_time)
            wake_key = f"alarm:{alarm.id}:v{alarm.schedule_version}:wake"
            existing_wake = self.notification_repo.find_by_idempotency_key(wake_key)

            if not existing_wake and wake_dt:
                leave_str = alarm.leave_time.strftime("%I:%M %p") if alarm.leave_time else ""
                arrival_str = alarm.desired_arrival_time.strftime("%I:%M %p") if alarm.desired_arrival_time else ""

                wake_notif = Notification(
                    user_id=alarm.user_id,
                    alarm_id=alarm.id,
                    type=NotificationType.ALARM_WAKE,
                    status=NotificationStatus.PENDING,
                    channel=NotificationChannel.ALL,
                    title=f"Wake up — {alarm.title or 'Alarm'}",
                    body=f"Good morning. You need to leave for {dest_name} by {leave_str} to arrive by {arrival_str}.",
                    scheduled_for=wake_dt,
                    schedule_version=alarm.schedule_version,
                    idempotency_key=wake_key,
                    metadata_json={
                        "action_url": f"/alarms/{alarm.id}",
                        "destination_name": dest_name,
                        "wake_time": wake_dt.isoformat(),
                        "leave_time": alarm.leave_time.isoformat() if alarm.leave_time else None,
                        "desired_arrival": alarm.desired_arrival_time.isoformat() if alarm.desired_arrival_time else None,
                    },
                )
                self.notification_repo.create(wake_notif)
                created.append(wake_notif)
                logger.info(
                    f"Scheduled ALARM_WAKE for Alarm {alarm.id} at {wake_dt.isoformat()} (v{alarm.schedule_version})"
                )

        # 2. Departure Reminder Event
        departure_enabled = user_pref.departure_reminder_enabled if user_pref else True
        if departure_enabled and alarm.leave_time:
            lead_mins = user_pref.departure_reminder_lead_minutes if user_pref else 10
            leave_dt = _ensure_tz(alarm.leave_time)
            if leave_dt:
                dept_reminder_dt = leave_dt - timedelta(minutes=lead_mins)
                now_utc = datetime.now(timezone.utc)

                if dept_reminder_dt > now_utc:
                    dept_key = f"alarm:{alarm.id}:v{alarm.schedule_version}:departure"
                    existing_dept = self.notification_repo.find_by_idempotency_key(dept_key)

                    if not existing_dept:
                        dept_notif = Notification(
                            user_id=alarm.user_id,
                            alarm_id=alarm.id,
                            type=NotificationType.ALARM_DEPARTURE_REMINDER,
                            status=NotificationStatus.PENDING,
                            channel=NotificationChannel.ALL,
                            title=f"Departure approaching — {alarm.title or 'Alarm'}",
                            body=f"Your departure for {dest_name} is in {lead_mins} minutes (at {leave_dt.strftime('%I:%M %p')}).",
                            scheduled_for=dept_reminder_dt,
                            schedule_version=alarm.schedule_version,
                            idempotency_key=dept_key,
                            metadata_json={
                                "action_url": f"/alarms/{alarm.id}",
                                "destination_name": dest_name,
                                "leave_time": leave_dt.isoformat(),
                                "lead_minutes": lead_mins,
                            },
                        )
                        self.notification_repo.create(dept_notif)
                        created.append(dept_notif)
                        logger.info(
                            f"Scheduled ALARM_DEPARTURE_REMINDER for Alarm {alarm.id} at {dept_reminder_dt.isoformat()} (v{alarm.schedule_version})"
                        )

        return created

    async def handle_schedule_changed(
        self,
        alarm: Alarm,
        previous_wake: Optional[datetime],
        new_wake: datetime,
        change_reason: str,
        is_urgent: bool = False,
        user_pref: Optional[UserPreference] = None,
    ) -> Notification:
        """
        Handles dynamic schedule adjustments triggered by real-time traffic recalculations (Step 8):
        1. Supersedes obsolete future notifications for previous versions.
        2. Creates an immediate actionable alert explaining what changed and why.
        3. Re-schedules updated wake and departure reminder events.
        """
        if not user_pref:
            user_pref = self.preference_repo.get_by_user(alarm.user_id)

        # 1. Supersede previous pending wake / departure reminders
        superseded_count = self.notification_repo.supersede_future_alarm_notifications(
            alarm.id, alarm.schedule_version
        )
        logger.info(
            f"Superseded {superseded_count} obsolete notifications for Alarm {alarm.id} prior to v{alarm.schedule_version}"
        )

        dest_name = alarm.destination.name if alarm.destination else "Destination"
        new_wake_tz = _ensure_tz(new_wake)
        now_utc = datetime.now(timezone.utc)

        # 2. Immediate Schedule Change / Urgent Alert
        change_key = f"alarm:{alarm.id}:v{alarm.schedule_version}:change"
        existing_change = self.notification_repo.find_by_idempotency_key(change_key)

        if existing_change:
            return existing_change

        if is_urgent or (new_wake_tz and new_wake_tz <= now_utc):
            notif_type = NotificationType.ALARM_URGENT_CHANGE
            title = "Urgent Schedule Change"
            body = (
                f"Severe traffic surge detected. Your new recommended wake time has already passed! "
                f"Please leave immediately for {dest_name} or recalculate your route."
            )
        else:
            notif_type = NotificationType.ALARM_SCHEDULE_CHANGED
            title = "Traffic Schedule Adjusted"
            new_wake_str = new_wake_tz.strftime("%I:%M %p") if new_wake_tz else ""
            leave_str = alarm.leave_time.strftime("%I:%M %p") if alarm.leave_time else ""
            body = (
                f"Traffic conditions changed ({change_reason}). "
                f"Your wake time has been adjusted to {new_wake_str} (leave by {leave_str})."
            )

        change_notif = Notification(
            user_id=alarm.user_id,
            alarm_id=alarm.id,
            type=notif_type,
            status=NotificationStatus.PENDING,
            channel=NotificationChannel.ALL,
            title=title,
            body=body,
            scheduled_for=now_utc,
            schedule_version=alarm.schedule_version,
            idempotency_key=change_key,
            metadata_json={
                "action_url": f"/alarms/{alarm.id}",
                "destination_name": dest_name,
                "reason": change_reason,
                "previous_wake": previous_wake.isoformat() if previous_wake else None,
                "new_wake": new_wake_tz.isoformat() if new_wake_tz else None,
                "is_urgent": is_urgent,
            },
        )
        self.notification_repo.create(change_notif)

        # Deliver the immediate alert asynchronously
        await self.deliver_notification(change_notif.id)

        # 3. Schedule updated wake and departure reminder events if alarm remains active
        if alarm.status in (AlarmStatus.ACTIVE, AlarmStatus.URGENT_SCHEDULE_CHANGE):
            self.schedule_alarm_notifications(alarm, user_pref)

        return change_notif

    def handle_alarm_disabled_or_cancelled(
        self, alarm_id: uuid.UUID, reason: str = "Alarm disabled or deleted"
    ) -> int:
        """Cancels all future pending notifications when an alarm is deactivated or removed."""
        return self.notification_repo.cancel_pending_alarm_notifications(alarm_id, reason)

    # -------------------------------------------------------------------------
    # Notification Delivery Engine
    # -------------------------------------------------------------------------

    async def deliver_notification(self, notification_id: uuid.UUID) -> DeliveryResult:
        """
        Delivers a single notification:
        - Claims the event using a distributed mutex
        - Validates alarm validity and schedule version freshness
        - Checks user preferences
        - Executes channel delivery via composite provider
        - Updates audit logs, delivery timestamps, and retry counts
        """
        lock_key = f"ada:notif:lock:{notification_id}"
        if not self._acquire_lock(lock_key, timeout=settings.NOTIFICATION_LOCK_TIMEOUT_SECONDS):
            logger.warning(f"Could not acquire lock for notification {notification_id}. Delivery skipped.")
            return DeliveryResult(
                success=False,
                provider_name="service",
                error_message="Lock conflict",
                is_transient=True,
            )

        try:
            notification = self.notification_repo.get_by_id(notification_id)
            if not notification:
                return DeliveryResult(
                    success=False,
                    provider_name="service",
                    error_message=f"Notification {notification_id} not found",
                )

            # Skip already handled notifications
            if notification.status in (
                NotificationStatus.DELIVERED,
                NotificationStatus.READ,
                NotificationStatus.CANCELLED,
                NotificationStatus.SUPERSEDED,
            ):
                return DeliveryResult(
                    success=True,
                    provider_name="service",
                    error_message=f"Notification is already in terminal state {notification.status}",
                )

            # 1. Alarm Integrity & Version Check
            if notification.alarm_id:
                alarm = self.alarm_repo.get(notification.alarm_id)
                if not alarm or alarm.status not in (AlarmStatus.ACTIVE, AlarmStatus.URGENT_SCHEDULE_CHANGE):
                    notification.status = NotificationStatus.CANCELLED
                    notification.last_error = "Associated alarm is no longer active"
                    self.notification_repo.update(notification)
                    logger.info(
                        f"Cancelled notification {notification_id}: Alarm {notification.alarm_id} is inactive"
                    )
                    return DeliveryResult(success=True, provider_name="service")

                # Verify Schedule Version Match
                if (
                    notification.schedule_version is not None
                    and alarm.schedule_version != notification.schedule_version
                    and notification.type in (NotificationType.ALARM_WAKE, NotificationType.ALARM_DEPARTURE_REMINDER)
                ):
                    notification.status = NotificationStatus.SUPERSEDED
                    notification.last_error = (
                        f"Superseded by newer schedule version {alarm.schedule_version}"
                    )
                    self.notification_repo.update(notification)
                    logger.info(
                        f"Superseded notification {notification_id}: v{notification.schedule_version} != current v{alarm.schedule_version}"
                    )
                    return DeliveryResult(success=True, provider_name="service")

            # 2. Preference Check
            user_pref = self.preference_repo.get_by_user(notification.user_id)
            if user_pref:
                if notification.type == NotificationType.ALARM_WAKE and not user_pref.wake_alarm_enabled:
                    notification.status = NotificationStatus.CANCELLED
                    notification.last_error = "Wake alarms disabled in user preferences"
                    self.notification_repo.update(notification)
                    return DeliveryResult(success=True, provider_name="service")

                if (
                    notification.type == NotificationType.ALARM_DEPARTURE_REMINDER
                    and not user_pref.departure_reminder_enabled
                ):
                    notification.status = NotificationStatus.CANCELLED
                    notification.last_error = "Departure reminders disabled in user preferences"
                    self.notification_repo.update(notification)
                    return DeliveryResult(success=True, provider_name="service")

                if (
                    notification.type in (NotificationType.ALARM_SCHEDULE_CHANGED, NotificationType.ALARM_URGENT_CHANGE)
                    and not user_pref.schedule_change_enabled
                ):
                    notification.status = NotificationStatus.CANCELLED
                    notification.last_error = "Schedule change notifications disabled in user preferences"
                    self.notification_repo.update(notification)
                    return DeliveryResult(success=True, provider_name="service")

            # 3. Channel Delivery Dispatch
            result = await self.delivery_provider.deliver(notification, user_pref)

            # 4. State Update
            self.notification_repo.record_delivery_attempt(
                notification=notification,
                success=result.success,
                error=result.error_message,
                max_retries=settings.MAX_NOTIFICATION_RETRIES,
                retry_backoff_seconds=settings.NOTIFICATION_RETRY_BACKOFF_SECONDS,
            )

            return result
        finally:
            self._release_lock(lock_key)

    async def process_due_notifications(
        self, current_time: Optional[datetime] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Batch-evaluates all pending notifications due at or before current_time.
        Executed periodically by the Celery Beat worker.
        """
        now_utc = _ensure_tz(current_time) or datetime.now(timezone.utc)
        due_list = self.notification_repo.get_due_notifications(now_utc, limit=limit)

        stats = {
            "evaluated": len(due_list),
            "delivered": 0,
            "failed": 0,
            "skipped": 0,
        }

        for notif in due_list:
            res = await self.deliver_notification(notif.id)
            if res.success:
                stats["delivered"] += 1
            elif res.is_transient:
                stats["skipped"] += 1
            else:
                stats["failed"] += 1

        logger.info(f"Processed {len(due_list)} due notifications: {stats}")
        return stats

    # -------------------------------------------------------------------------
    # User Preferences & Subscription Endpoints Support
    # -------------------------------------------------------------------------

    def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Notification], int, int]:
        items = self.notification_repo.get_by_user(
            user_id=user_id, unread_only=unread_only, limit=limit, offset=offset
        )
        total = self.notification_repo.count_by_user(user_id=user_id, unread_only=False)
        unread_count = self.notification_repo.get_unread_count(user_id=user_id)
        return items, total, unread_count

    def get_unread_count(self, user_id: uuid.UUID) -> int:
        return self.notification_repo.get_unread_count(user_id=user_id)

    def mark_notification_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Notification]:
        return self.notification_repo.mark_as_read(notification_id, user_id)

    def mark_all_notifications_read(self, user_id: uuid.UUID) -> int:
        return self.notification_repo.mark_all_as_read(user_id)

    def get_preferences(self, user_id: uuid.UUID) -> NotificationPreferencesResponse:
        pref = self.preference_repo.get_by_user(user_id)
        if not pref:
            return NotificationPreferencesResponse()
        return NotificationPreferencesResponse(
            wake_alarm_enabled=pref.wake_alarm_enabled,
            departure_reminder_enabled=pref.departure_reminder_enabled,
            departure_reminder_lead_minutes=pref.departure_reminder_lead_minutes,
            schedule_change_enabled=pref.schedule_change_enabled,
            traffic_change_enabled=pref.traffic_change_enabled,
            sound_enabled=pref.sound_enabled,
            vibration_enabled=pref.vibration_enabled,
            in_app_enabled=pref.in_app_enabled,
            web_push_enabled=pref.web_push_enabled,
        )

    def update_preferences(
        self, user_id: uuid.UUID, data: NotificationPreferencesUpdate
    ) -> NotificationPreferencesResponse:
        pref = self.preference_repo.get_by_user(user_id)
        if not pref:
            pref = UserPreference(user_id=user_id)
            self.preference_repo.create(pref)

        for field, value in data.model_dump(exclude_unset=True).items():
            if hasattr(pref, field) and value is not None:
                setattr(pref, field, value)

        self.preference_repo.update(pref)
        return self.get_preferences(user_id)

    def register_push_subscription(
        self,
        user_id: uuid.UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: Optional[str] = None,
    ) -> PushSubscription:
        return self.push_repo.create_or_update(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
        )

    def unregister_push_subscription(self, user_id: uuid.UUID, endpoint: str) -> bool:
        return self.push_repo.delete_by_user_and_endpoint(user_id, endpoint)

    async def send_test_notification(
        self, user_id: uuid.UUID, test_req: NotificationTestRequest
    ) -> Notification:
        """Dispatches an immediate test notification to verify delivery channels."""
        now_utc = datetime.now(timezone.utc)
        notif = Notification(
            user_id=user_id,
            type=test_req.type or NotificationType.SYSTEM,
            status=NotificationStatus.PENDING,
            channel=NotificationChannel.ALL,
            title=test_req.title or "ADA Alarm Test",
            body=test_req.body or "This is a test notification confirming delivery.",
            scheduled_for=now_utc,
            idempotency_key=f"test:{user_id}:{now_utc.timestamp()}",
            metadata_json={"test": True, "action_url": "/settings"},
        )
        self.notification_repo.create(notif)
        await self.deliver_notification(notif.id)
        return notif
