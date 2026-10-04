from __future__ import annotations

import enum
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    Uuid,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.destination import Destination
    from app.models.notification import Notification
    from app.models.schedule import AlarmSchedule
    from app.models.schedule_change import AlarmScheduleChange
    from app.models.user import User


class TransportMode(str, enum.Enum):
    DRIVING = "driving"
    TRANSIT = "transit"
    BICYCLING = "bicycling"
    WALKING = "walking"


class AlarmStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"
    URGENT_SCHEDULE_CHANGE = "urgent_schedule_change"
    MISSED_RECALCULATION = "missed_recalculation"


class Alarm(Base, TimestampMixin):
    """
    Core Alarm domain entity.
    Represents: "I need to arrive at this destination at this arrival_time."
    The calculated_wake_time, calculated_leave_time, and planned_arrival_time
    are managed by ADA's Smart Adaptive Alarm Engine.
    """

    __tablename__ = "alarms"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)

    # Core schedule parameters
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False, index=True)
    preparation_time: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # minutes
    safety_buffer: Mapped[int] = mapped_column(Integer, default=15, nullable=False)  # minutes
    transportation_mode: Mapped[TransportMode] = mapped_column(
        SQLEnum(
            TransportMode,
            name="transport_mode_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TransportMode.DRIVING,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Smart Alarm state machine
    status: Mapped[AlarmStatus] = mapped_column(
        SQLEnum(
            AlarmStatus,
            name="alarm_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AlarmStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # Dynamically calculated outputs (recomputable cache populated by ETA engine)
    calculated_wake_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    calculated_leave_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    planned_arrival_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_travel_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, nullable=True
    )
    traffic_delay_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, nullable=True
    )
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timezone & versioning metadata
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Kolkata", nullable=False
    )
    calculation_version: Mapped[str] = mapped_column(
        String(30), default="eta-v1", nullable=False
    )
    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Step 8: Dynamic Recalculation & Schedule Versioning
    schedule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_route_refresh_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_schedule_change_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    schedule_change_reason: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    route_freshness_state: Mapped[str] = mapped_column(
        String(50), default="fresh", nullable=False
    )

    # Optional origin overrides
    origin_lat: Mapped[Optional[float]] = mapped_column(nullable=True)
    origin_lng: Mapped[Optional[float]] = mapped_column(nullable=True)
    origin_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Step 10: Weather & Calendar Context Snapshot
    weather_buffer_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, default=0, nullable=True
    )
    weather_condition_snapshot: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    calendar_event_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alarms")
    destination: Mapped["Destination"] = relationship("Destination", back_populates="alarms")
    schedule: Mapped[Optional["AlarmSchedule"]] = relationship(
        "AlarmSchedule",
        back_populates="alarm",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    schedule_changes: Mapped[list["AlarmScheduleChange"]] = relationship(
        "AlarmScheduleChange",
        back_populates="alarm",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AlarmScheduleChange.created_at.desc()",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="alarm",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Notification.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_alarms_user_id_status", "user_id", "status"),
        Index("ix_alarms_enabled_wake_time", "enabled", "calculated_wake_time"),
    )

    @property
    def name(self) -> str:
        return self.title

    @property
    def wake_time(self) -> Optional[datetime]:
        return self.calculated_wake_time

    @property
    def leave_time(self) -> Optional[datetime]:
        return self.calculated_leave_time

    @property
    def preparation_duration_seconds(self) -> int:
        return self.preparation_time * 60

    @property
    def safety_buffer_seconds(self) -> int:
        return self.safety_buffer * 60

    @property
    def desired_arrival_time(self) -> time:
        return self.arrival_time

    @property
    def is_active(self) -> bool:
        return self.enabled
