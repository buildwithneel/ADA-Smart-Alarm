from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.alarm import TransportMode
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class DistanceUnit(str, enum.Enum):
    KM = "km"
    MI = "mi"


class TimeFormat(str, enum.Enum):
    H12 = "12h"
    H24 = "24h"


class ThemeMode(str, enum.Enum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class UserPreference(Base, TimestampMixin):
    """
    User Preferences entity storing persistent configuration.
    Excludes temporary UI state while preserving user defaults.
    """

    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Defaults
    default_transportation: Mapped[TransportMode] = mapped_column(
        SQLEnum(
            TransportMode,
            name="transport_mode_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TransportMode.DRIVING,
        nullable=False,
    )
    default_preparation_time: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )  # minutes
    default_safety_buffer: Mapped[int] = mapped_column(
        Integer, default=15, nullable=False
    )  # minutes

    # Units & Appearance
    distance_units: Mapped[DistanceUnit] = mapped_column(
        SQLEnum(
            DistanceUnit,
            name="distance_unit_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DistanceUnit.KM,
        nullable=False,
    )
    time_format: Mapped[TimeFormat] = mapped_column(
        SQLEnum(
            TimeFormat,
            name="time_format_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TimeFormat.H12,
        nullable=False,
    )
    theme: Mapped[ThemeMode] = mapped_column(
        SQLEnum(
            ThemeMode,
            name="theme_mode_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ThemeMode.DARK,
        nullable=False,
    )

    # Notification preferences
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vibration_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pre_alarm_notification: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    wake_alarm_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    departure_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    departure_reminder_lead_minutes: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )
    schedule_change_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    traffic_change_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    web_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Step 10: Weather & Calendar Context Intelligence Preferences
    weather_buffer_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    weather_buffer_mode: Mapped[str] = mapped_column(
        String(50), default="informational_only", nullable=False
    )
    weather_buffer_minutes: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )
    weather_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    calendar_sync_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    calendar_auto_reschedule: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Step 11: AI Assistant & Personalization Preferences
    assistant_response_style: Mapped[str] = mapped_column(
        String(50), default="concise", nullable=False
    )
    save_conversation_history: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    use_alarm_history_suggestions: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preference")
