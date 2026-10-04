from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alarm import Alarm
    from app.models.user import User


class DestinationType(str, enum.Enum):
    HOME = "home"
    COLLEGE = "college"
    OFFICE = "office"
    GYM = "gym"
    AIRPORT = "airport"
    CUSTOM = "custom"


class Destination(Base, TimestampMixin):
    """
    Destination entity representing a saved or frequent location.
    Provider-agnostic design accommodating Google Places or Mapbox Geocoding identifiers.
    """

    __tablename__ = "destinations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[DestinationType] = mapped_column(
        SQLEnum(
            DestinationType,
            name="destination_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DestinationType.CUSTOM,
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    place_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "google", "mapbox", "custom"
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="destinations")
    alarms: Mapped[List["Alarm"]] = relationship(
        "Alarm",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_destinations_user_id_favorite", "user_id", "is_favorite"),
    )
