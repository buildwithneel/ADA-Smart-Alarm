import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("ada.events")


class AlarmEventType(str, enum.Enum):
    ALARM_SCHEDULED = "alarm.scheduled"
    ALARM_UPDATED = "alarm.updated"
    ALARM_DISABLED = "alarm.disabled"
    ALARM_EXPIRED = "alarm.expired"
    ALARM_COMPLETED = "alarm.completed"
    ALARM_CANCELLED = "alarm.cancelled"
    ALARM_RECALCULATED = "alarm.recalculated"
    ALARM_URGENT_CHANGE = "alarm.urgent_change"
    ALARM_REFRESH_SKIPPED = "alarm.refresh_skipped"
    # Step 10: Weather + Calendar Context Events
    CONTEXT_WEATHER_ALERT = "context.weather_alert"
    CONTEXT_WEATHER_BUFFER_APPLIED = "context.weather_buffer_applied"
    CALENDAR_EVENT_SYNCED = "calendar.event_synced"
    CALENDAR_EVENT_CHANGED = "calendar.event_changed"
    CALENDAR_ALARM_CREATED = "calendar.alarm_created"


class AlarmEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AlarmEventType
    alarm_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)


_EVENT_LISTENERS: list[Any] = []


def register_alarm_event_listener(listener: Any) -> None:
    """Register a callback listener for AlarmEvent domain events."""
    if listener not in _EVENT_LISTENERS:
        _EVENT_LISTENERS.append(listener)


def publish_alarm_event(event: AlarmEvent) -> None:
    """
    Publish domain event for decoupled event handling.
    Dispatches to registered event listeners (e.g. NotificationDeliveryService).
    """
    logger.info(
        f"Domain Event: {event.event_type.value} | Alarm: {event.alarm_id} | User: {event.user_id}",
        extra={
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "alarm_id": event.alarm_id,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
        },
    )

    for listener in list(_EVENT_LISTENERS):
        try:
            listener(event)
        except Exception as exc:
            logger.error(
                f"Error in domain event listener {getattr(listener, '__name__', str(listener))}: {exc}",
                exc_info=True,
            )
