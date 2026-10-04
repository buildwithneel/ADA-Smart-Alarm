from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm
    from app.models.user import User


class NotificationType(str, enum.Enum):
    ALARM_WAKE = "ALARM_WAKE"
    ALARM_DEPARTURE_REMINDER = "ALARM_DEPARTURE_REMINDER"
    ALARM_SCHEDULE_CHANGED = "ALARM_SCHEDULE_CHANGED"
    ALARM_URGENT_CHANGE = "ALARM_URGENT_CHANGE"
    ALARM_MISSED = "ALARM_MISSED"
    ALARM_COMPLETED = "ALARM_COMPLETED"
    ALARM_CANCELLED = "ALARM_CANCELLED"
    SYSTEM = "SYSTEM"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    WEB_PUSH = "WEB_PUSH"
    ALL = "ALL"


class Notification(Base, TimestampMixin):
    """
    Persistent notification entity for in-app history, scheduled alarm delivery,
    and push notification dispatch with idempotency and optimistic concurrency.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alarm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("alarms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(
            NotificationStatus,
            name="notification_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(
            NotificationChannel,
            name="notification_channel_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=NotificationChannel.ALL,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    schedule_version: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(160),
        unique=True,
        nullable=True,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    alarm: Mapped[Optional["Alarm"]] = relationship("Alarm", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_id_status", "user_id", "status"),
        Index("ix_notifications_scheduled_for_status", "scheduled_for", "status"),
    )
