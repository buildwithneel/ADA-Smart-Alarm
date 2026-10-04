from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm


class ScheduleType(str, enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    CUSTOM = "custom"


class AlarmSchedule(Base, TimestampMixin):
    """
    Recurring or one-time schedule definition linked to an Alarm entity.
    Allows recurring alarms without duplicating the core Alarm domain record.
    """

    __tablename__ = "alarm_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    alarm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alarms.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SQLEnum(
            ScheduleType,
            name="schedule_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ScheduleType.DAILY,
        nullable=False,
    )
    # Comma-separated list for custom schedules: e.g. "MON,TUE,WED,THU,FRI"
    repeat_days: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # For one-time alarms
    specific_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    alarm: Mapped["Alarm"] = relationship("Alarm", back_populates="schedule")
