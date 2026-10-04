from __future__ import annotations

import enum
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import ForbiddenException, NotFoundException, ValidationException
from app.core.events import AlarmEvent, AlarmEventType, publish_alarm_event
from app.models.alarm import Alarm, AlarmStatus
from app.models.preference import UserPreference
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.services.alarm_recalculation_service import AlarmRecalculationService, RecalculationResult
from app.services.calendar.calendar_service import CalendarService
from app.services.weather.weather_service import JourneyWeatherSummary, WeatherService

logger = logging.getLogger("ada.services.context")


class ContextType(str, enum.Enum):
    WEATHER = "weather"
    CALENDAR = "calendar"


class ContextRelevance(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ContextFinding(str, enum.Enum):
    CLEAR_CONDITIONS = "CLEAR_CONDITIONS"
    RAIN_DURING_JOURNEY = "RAIN_DURING_JOURNEY"
    SEVERE_WEATHER_ALERT = "SEVERE_WEATHER_ALERT"
    CALENDAR_EVENT_TIME_CHANGED = "CALENDAR_EVENT_TIME_CHANGED"
    CALENDAR_EVENT_LOCATION_CHANGED = "CALENDAR_EVENT_LOCATION_CHANGED"
    CALENDAR_EVENT_CANCELLED = "CALENDAR_EVENT_CANCELLED"
    CONTEXT_DATA_UNAVAILABLE = "CONTEXT_DATA_UNAVAILABLE"


class ContextAction(str, enum.Enum):
    NONE = "none"
    WARN_USER = "warn_user"
    APPLY_BUFFER = "apply_buffer"
    RESCHEDULE_ARRIVAL = "reschedule_arrival"
    CANCEL_ALARM = "cancel_alarm"


class ContextResult(BaseModel):
    """
    Normalized, explainable context evaluation result for ADA alarms.
    """
    context_type: ContextType
    source: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_time_window: Dict[str, Optional[str]] = Field(default_factory=dict)
    freshness: str = "fresh"  # fresh, stale, expired
    relevance: ContextRelevance = ContextRelevance.NONE
    finding: ContextFinding = ContextFinding.CLEAR_CONDITIONS
    recommended_action: ContextAction = ContextAction.NONE
    recommended_buffer_minutes: int = 0
    requires_confirmation: bool = True
    explanation: str = ""
    policy_version: str = "v1"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextService:
    """
    Step 10 Context Intelligence Engine.
    Evaluates weather forecasts, calendar events, and journey conditions
    against user-configured policies without arbitrary multipliers.
    """

    def __init__(
        self,
        alarm_repo: AlarmRepository,
        destination_repo: DestinationRepository,
        pref_repo: PreferenceRepository,
        calendar_repo: CalendarRepository,
        weather_service: Optional[WeatherService] = None,
        calendar_service: Optional[CalendarService] = None,
    ):
        self.alarm_repo = alarm_repo
        self.destination_repo = destination_repo
        self.pref_repo = pref_repo
        self.calendar_repo = calendar_repo
        self.weather_service = weather_service or WeatherService()
        self.calendar_service = calendar_service

    # ------------------------------------------------------------------
    # Context Evaluation
    # ------------------------------------------------------------------

    async def evaluate_alarm_context(
        self, alarm_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> List[ContextResult]:
        """
        Evaluates all contextual sources (Weather + Calendar) for a given alarm.
        Produces explainable recommendations grounded in actual journey parameters.
        """
        alarm = self.alarm_repo.get(alarm_id)
        if not alarm:
            raise NotFoundException(f"Alarm {alarm_id} not found.")

        if user_id and alarm.user_id != user_id:
            raise ForbiddenException("You do not have access to this alarm.")

        user_pref = self.pref_repo.get_by_user_id(alarm.user_id)
        results: List[ContextResult] = []

        # 1. Weather Context Evaluation
        try:
            weather_res = await self._evaluate_weather_context(alarm, user_pref)
            if weather_res:
                results.append(weather_res)
        except Exception as exc:
            logger.warning(f"Weather evaluation failed for alarm {alarm_id}: {exc}")
            results.append(
                ContextResult(
                    context_type=ContextType.WEATHER,
                    source=self.weather_service.provider.provider_name,
                    freshness="stale",
                    relevance=ContextRelevance.NONE,
                    finding=ContextFinding.CONTEXT_DATA_UNAVAILABLE,
                    recommended_action=ContextAction.NONE,
                    explanation="Weather data is currently unavailable. Alarm schedule remains unchanged.",
                )
            )

        # 2. Calendar Context Evaluation
        try:
            calendar_res = await self._evaluate_calendar_context(alarm, user_pref)
            if calendar_res:
                results.append(calendar_res)
        except Exception as exc:
            logger.warning(f"Calendar evaluation failed for alarm {alarm_id}: {exc}")

        return results

    async def _evaluate_weather_context(
        self, alarm: Alarm, user_pref: Optional[UserPreference]
    ) -> Optional[ContextResult]:
        dest = self.destination_repo.get(alarm.destination_id)
        if not dest:
            return None

        # Determine journey window
        now = datetime.now(timezone.utc)
        arrival_dt = alarm.planned_arrival_time or (now + timedelta(hours=1))
        leave_dt = alarm.calculated_leave_time or (arrival_dt - timedelta(minutes=30))

        origin_lat = alarm.origin_lat
        origin_lng = alarm.origin_lng

        weather_summary: JourneyWeatherSummary = await self.weather_service.evaluate_journey_weather(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest.latitude,
            dest_lng=dest.longitude,
            leave_time=leave_dt,
            arrival_time=arrival_dt,
        )

        valid_window = {
            "start": leave_dt.isoformat() if leave_dt else None,
            "end": arrival_dt.isoformat() if arrival_dt else None,
        }

        freshness_label = "stale" if weather_summary.is_stale else "fresh"

        # Determine user preferences
        buffer_enabled = user_pref.weather_buffer_enabled if user_pref else False
        buffer_mode = user_pref.weather_buffer_mode if user_pref else "informational_only"
        max_buf = min(
            user_pref.weather_buffer_minutes if user_pref else settings.WEATHER_BUFFER_DEFAULT_MINUTES,
            settings.WEATHER_BUFFER_MAX_MINUTES,
        )

        # Severe Weather Alert takes highest priority
        if weather_summary.is_severe:
            alert_details = [
                {"title": a.title, "description": a.description, "source": a.source, "url": a.official_url}
                for a in weather_summary.alerts
            ]
            return ContextResult(
                context_type=ContextType.WEATHER,
                source=weather_summary.provider,
                valid_time_window=valid_window,
                freshness=freshness_label,
                relevance=ContextRelevance.HIGH,
                finding=ContextFinding.SEVERE_WEATHER_ALERT,
                recommended_action=ContextAction.WARN_USER,
                recommended_buffer_minutes=0,  # Never silently alter alarm solely because severe alert exists
                requires_confirmation=False,
                explanation=f"Severe weather alert reported during your journey: {weather_summary.condition_text}. Caution advised. Your alarm schedule is preserved.",
                metadata={
                    "alerts": alert_details,
                    "condition": weather_summary.condition.value,
                    "attribution": weather_summary.attribution,
                },
            )

        # Rain or Qualifying Precipitation
        if weather_summary.has_precipitation:
            alarm.weather_condition_snapshot = weather_summary.condition_text
            self.alarm_repo.db.flush()

            if buffer_enabled and buffer_mode == "automatic":
                action = ContextAction.APPLY_BUFFER
                req_conf = False
                explanation = f"{weather_summary.condition_text} expected during your journey. Configured weather policy adds {max_buf} minutes to the safety buffer."
            elif buffer_enabled and buffer_mode == "user_confirmed":
                action = ContextAction.APPLY_BUFFER
                req_conf = True
                explanation = f"{weather_summary.condition_text} expected during your journey. Recommended adjustment: allow {max_buf} additional minutes. Your current alarm has not changed."
            else:
                action = ContextAction.WARN_USER
                req_conf = False
                explanation = f"{weather_summary.condition_text} expected during your journey. Travel conditions may be affected. Your current alarm has not changed."

            return ContextResult(
                context_type=ContextType.WEATHER,
                source=weather_summary.provider,
                valid_time_window=valid_window,
                freshness=freshness_label,
                relevance=ContextRelevance.HIGH if buffer_enabled else ContextRelevance.MEDIUM,
                finding=ContextFinding.RAIN_DURING_JOURNEY,
                recommended_action=action,
                recommended_buffer_minutes=max_buf if action == ContextAction.APPLY_BUFFER else 0,
                requires_confirmation=req_conf,
                explanation=explanation,
                metadata={
                    "condition": weather_summary.condition.value,
                    "condition_text": weather_summary.condition_text,
                    "precipitation_mm": weather_summary.precipitation_mm,
                    "temperature_c": weather_summary.temperature_c,
                    "attribution": weather_summary.attribution,
                    "weather_buffer_mode": buffer_mode,
                },
            )

        # Clear conditions
        return ContextResult(
            context_type=ContextType.WEATHER,
            source=weather_summary.provider,
            valid_time_window=valid_window,
            freshness=freshness_label,
            relevance=ContextRelevance.NONE,
            finding=ContextFinding.CLEAR_CONDITIONS,
            recommended_action=ContextAction.NONE,
            recommended_buffer_minutes=0,
            requires_confirmation=False,
            explanation=f"Forecast indicates {weather_summary.condition_text.lower()} conditions for your journey.",
            metadata={
                "condition": weather_summary.condition.value,
                "temperature_c": weather_summary.temperature_c,
                "attribution": weather_summary.attribution,
            },
        )

    async def _evaluate_calendar_context(
        self, alarm: Alarm, user_pref: Optional[UserPreference]
    ) -> Optional[ContextResult]:
        if not alarm.calendar_event_id:
            return None

        event = self.calendar_repo.get_event_by_alarm(alarm.id)
        if not event:
            return None

        valid_window = {
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
        }

        auto_reschedule = user_pref.calendar_auto_reschedule if user_pref else False

        # Event Cancelled
        if event.status == "cancelled":
            return ContextResult(
                context_type=ContextType.CALENDAR,
                source=event.source_provider,
                valid_time_window=valid_window,
                freshness="fresh",
                relevance=ContextRelevance.HIGH,
                finding=ContextFinding.CALENDAR_EVENT_CANCELLED,
                recommended_action=ContextAction.WARN_USER,
                requires_confirmation=True,
                explanation=f"Linked calendar event '{event.title}' was cancelled. Your ADA alarm has not been deleted.",
                metadata={"external_event_id": event.external_event_id},
            )

        # Event Time Changed
        alarm_tz = ZoneInfo(alarm.timezone) if alarm.timezone else timezone.utc
        event_time = event.start_time.astimezone(alarm_tz).time()

        if alarm.arrival_time != event_time:
            time_diff_mins = (
                (event.start_time.astimezone(alarm_tz).hour * 60 + event.start_time.astimezone(alarm_tz).minute)
                - (alarm.arrival_time.hour * 60 + alarm.arrival_time.minute)
            )
            return ContextResult(
                context_type=ContextType.CALENDAR,
                source=event.source_provider,
                valid_time_window=valid_window,
                freshness="fresh",
                relevance=ContextRelevance.HIGH,
                finding=ContextFinding.CALENDAR_EVENT_TIME_CHANGED,
                recommended_action=ContextAction.RESCHEDULE_ARRIVAL,
                requires_confirmation=not auto_reschedule,
                explanation=(
                    f"Linked calendar event '{event.title}' moved to {event_time.strftime('%I:%M %p')}. "
                    + ("Schedule automatically adjusted." if auto_reschedule else "Recalculation recommended.")
                ),
                metadata={
                    "new_arrival_time": event_time.strftime("%H:%M:%S"),
                    "time_diff_mins": time_diff_mins,
                    "auto_rescheduled": auto_reschedule,
                },
            )

        return None

    # ------------------------------------------------------------------
    # Apply Context Adjustments (Step 8 & 9 Recalculation Integration)
    # ------------------------------------------------------------------

    async def apply_weather_buffer(
        self,
        alarm_id: uuid.UUID,
        user_id: uuid.UUID,
        buffer_minutes: Optional[int] = None,
        expected_version: Optional[int] = None,
    ) -> RecalculationResult:
        """
        Explicitly applies user-approved or auto-approved weather buffer through
        the existing AlarmRecalculationService, respecting schedule versioning.
        """
        alarm = self.alarm_repo.get(alarm_id)
        if not alarm:
            raise NotFoundException("Alarm not found.")
        if alarm.user_id != user_id:
            raise ForbiddenException("You do not own this alarm.")

        user_pref = self.pref_repo.get_by_user_id(user_id)
        minutes_to_apply = (
            buffer_minutes
            if buffer_minutes is not None
            else (user_pref.weather_buffer_minutes if user_pref else 10)
        )
        minutes_to_apply = min(max(0, minutes_to_apply), settings.WEATHER_BUFFER_MAX_MINUTES)

        recalc_service = AlarmRecalculationService(
            self.alarm_repo, self.destination_repo
        )

        result = await recalc_service.recalculate_alarm(
            alarm_id=alarm_id,
            user_id=user_id,
            expected_version=expected_version,
            weather_buffer_minutes=minutes_to_apply,
            schedule_reason_override="WEATHER_BUFFER_APPLIED",
            force=True,
        )

        if result.schedule_changed:
            publish_alarm_event(
                AlarmEvent(
                    event_type=AlarmEventType.CONTEXT_WEATHER_BUFFER_APPLIED,
                    alarm_id=str(alarm.id),
                    user_id=str(user_id),
                    payload={
                        "weather_buffer_minutes": minutes_to_apply,
                        "schedule_version": result.schedule_version,
                        "new_wake_time": result.new_wake_time.isoformat() if result.new_wake_time else None,
                        "new_leave_time": result.new_leave_time.isoformat() if result.new_leave_time else None,
                    },
                )
            )

        return result
