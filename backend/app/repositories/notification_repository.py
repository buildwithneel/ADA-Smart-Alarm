from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger("ada.repositories.notification")


class NotificationRepository(BaseRepository[Notification]):
    """
    Repository for managing persistent notification delivery records, audit logs,
    and due-event scheduling queues.
    """

    def __init__(self, db: Session):
        super().__init__(Notification, db)

    def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[NotificationStatus] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            # Unread means delivered or sent, but read_at is null
            stmt = stmt.where(
                Notification.read_at.is_(None),
                Notification.status.in_([NotificationStatus.DELIVERED, NotificationStatus.SENT]),
            )
        elif status:
            stmt = stmt.where(Notification.status == status)
        else:
            # By default in user view, show delivered, read, sent, or failed notifications
            stmt = stmt.where(
                Notification.status.in_(
                    [
                        NotificationStatus.DELIVERED,
                        NotificationStatus.READ,
                        NotificationStatus.SENT,
                        NotificationStatus.FAILED,
                    ]
                )
            )

        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_by_user(self, user_id: uuid.UUID, unread_only: bool = False) -> int:
        stmt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(
                Notification.read_at.is_(None),
                Notification.status.in_([NotificationStatus.DELIVERED, NotificationStatus.SENT]),
            )
        else:
            stmt = stmt.where(
                Notification.status.in_(
                    [
                        NotificationStatus.DELIVERED,
                        NotificationStatus.READ,
                        NotificationStatus.SENT,
                        NotificationStatus.FAILED,
                    ]
                )
            )
        return int(self.db.scalar(stmt) or 0)

    def get_unread_count(self, user_id: uuid.UUID) -> int:
        return self.count_by_user(user_id=user_id, unread_only=True)

    def mark_as_read(self, id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        stmt = (
            update(Notification)
            .where(Notification.id == id, Notification.user_id == user_id)
            .values(read_at=datetime.now(timezone.utc), status=NotificationStatus.READ)
            .returning(Notification)
        )
        result = self.db.scalars(stmt).first()
        self.db.commit()
        return result

    def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.status.in_([NotificationStatus.DELIVERED, NotificationStatus.SENT]),
            )
            .values(read_at=datetime.now(timezone.utc), status=NotificationStatus.READ)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

    def get_due_notifications(
        self, current_time: datetime, limit: int = 100
    ) -> List[Notification]:
        """
        Fetch notifications that are scheduled to deliver at or before current_time.
        Ordered by scheduled_for ascending.
        """
        stmt = (
            select(Notification)
            .where(
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_for <= current_time,
            )
            .order_by(Notification.scheduled_for.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def find_by_idempotency_key(self, key: str) -> Optional[Notification]:
        stmt = select(Notification).where(Notification.idempotency_key == key)
        return self.db.scalars(stmt).first()

    def supersede_future_alarm_notifications(
        self, alarm_id: uuid.UUID, current_schedule_version: int
    ) -> int:
        """
        Marks any pending scheduled notifications for this alarm with an older version as SUPERSEDED.
        Prevents dual-firing when traffic recalculation adjusts wake/leave times.
        """
        stmt = (
            update(Notification)
            .where(
                Notification.alarm_id == alarm_id,
                Notification.status == NotificationStatus.PENDING,
                Notification.type.in_([NotificationType.ALARM_WAKE, NotificationType.ALARM_DEPARTURE_REMINDER]),
                Notification.schedule_version < current_schedule_version,
            )
            .values(
                status=NotificationStatus.SUPERSEDED,
                last_error=f"Superseded by schedule version {current_schedule_version}",
            )
        )
        result = self.db.execute(stmt)
        self.db.commit()
        logger.info(
            f"Superseded {result.rowcount} pending notifications for Alarm {alarm_id} (version < {current_schedule_version})"
        )
        return result.rowcount

    def cancel_pending_alarm_notifications(
        self, alarm_id: uuid.UUID, reason: str = "Alarm disabled or deleted"
    ) -> int:
        """
        Cancels all pending scheduled notifications for this alarm.
        """
        stmt = (
            update(Notification)
            .where(
                Notification.alarm_id == alarm_id,
                Notification.status == NotificationStatus.PENDING,
            )
            .values(
                status=NotificationStatus.CANCELLED,
                last_error=reason,
            )
        )
        result = self.db.execute(stmt)
        self.db.commit()
        logger.info(f"Cancelled {result.rowcount} pending notifications for Alarm {alarm_id}: {reason}")
        return result.rowcount

    def record_delivery_attempt(
        self,
        notification: Notification,
        success: bool,
        error: Optional[str] = None,
        max_retries: int = 3,
        retry_backoff_seconds: int = 60,
    ) -> Notification:
        """
        Records the delivery attempt state. If failed and retries remain, schedules retry with backoff.
        If max retries reached, marks FAILED.
        """
        now = datetime.now(timezone.utc)
        if success:
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = now
            notification.last_error = None
        else:
            notification.retry_count += 1
            notification.last_error = error
            if notification.retry_count >= max_retries:
                notification.status = NotificationStatus.FAILED
                logger.error(
                    f"Notification {notification.id} delivery FAILED after {notification.retry_count} attempts: {error}"
                )
            else:
                # Schedule retry with exponential backoff
                backoff_delay = retry_backoff_seconds * (2 ** (notification.retry_count - 1))
                notification.scheduled_for = now + timedelta(seconds=backoff_delay)
                logger.warning(
                    f"Notification {notification.id} attempt {notification.retry_count} failed ({error}). Retrying in {backoff_delay}s"
                )

        self.db.commit()
        self.db.refresh(notification)
        return notification
