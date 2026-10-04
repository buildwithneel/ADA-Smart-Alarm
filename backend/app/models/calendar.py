from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm
    from app.models.user import User


class CalendarConnection(Base, TimestampMixin):
    """
    Authorized Calendar Provider Connection (e.g. Google Calendar OAuth 2.0).
    Sensitive access and refresh tokens are encrypted at rest using Fernet.
    """

    __tablename__ = "calendar_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)
    account_email: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[str] = mapped_column(
        String(500),
        default="https://www.googleapis.com/auth/calendar.events.readonly",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_status: Mapped[str] = mapped_column(
        String(50), default="idle", nullable=False
    )  # idle, syncing, success, error
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="calendar_connections")
    events: Mapped[List["CalendarEvent"]] = relationship(
        "CalendarEvent",
        back_populates="connection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CalendarEvent(Base, TimestampMixin):
    """
    Normalized calendar event retrieved from an authorized calendar provider.
    Adheres strictly to data minimization (no description or private attendees stored).
    """

    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calendar_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alarm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("alarms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_event_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resolved_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolved_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="confirmed", nullable=False
    )  # confirmed, tentative, cancelled
    source_provider: Mapped[str] = mapped_column(
        String(50), default="google", nullable=False
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    event_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    connection: Mapped["CalendarConnection"] = relationship(
        "CalendarConnection", back_populates="events"
    )
    user: Mapped["User"] = relationship("User", back_populates="calendar_events")
    alarm: Mapped[Optional["Alarm"]] = relationship("Alarm")
