from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm


class AlarmScheduleChange(Base, TimestampMixin):
    """
    Lightweight audit record of meaningful schedule changes.
    Tracks adjustments triggered by real-time traffic increases, decreases,
    or urgent schedule modifications.
    """

    __tablename__ = "alarm_schedule_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    alarm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alarms.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Historical timeline comparison
    previous_wake_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_wake_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_leave_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_leave_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_planned_arrival: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_planned_arrival: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Duration deltas
    previous_travel_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    new_travel_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    # Auditing metadata
    reason: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    schedule_version: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    # Relationship
    alarm: Mapped["Alarm"] = relationship(
        "Alarm", back_populates="schedule_changes"
    )
