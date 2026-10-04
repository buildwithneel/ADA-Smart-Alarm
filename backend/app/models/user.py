from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm
    from app.models.calendar import CalendarConnection, CalendarEvent
    from app.models.destination import Destination
    from app.models.notification import Notification
    from app.models.preference import UserPreference
    from app.models.push_subscription import PushSubscription


class User(Base, TimestampMixin):
    """
    User entity representing an ADA account owner.
    Synced with Firebase Authentication UID as the authoritative external identity key.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    destinations: Mapped[List["Destination"]] = relationship(
        "Destination",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alarms: Mapped[List["Alarm"]] = relationship(
        "Alarm",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    preference: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    push_subscriptions: Mapped[List["PushSubscription"]] = relationship(
        "PushSubscription",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    calendar_connections: Mapped[List["CalendarConnection"]] = relationship(
        "CalendarConnection",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    calendar_events: Mapped[List["CalendarEvent"]] = relationship(
        "CalendarEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
