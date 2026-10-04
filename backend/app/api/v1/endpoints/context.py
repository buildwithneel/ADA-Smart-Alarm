from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.alarm import AlarmResponse
from app.schemas.context import (
    ApplyWeatherBufferRequest,
    ContextResultResponse,
    ContextSummaryResponse,
)
from app.schemas.weather import WeatherDataSchema
from app.services.context.context_service import (
    ContextAction,
    ContextFinding,
    ContextResult,
    ContextService,
    ContextType,
)
from app.services.weather.weather_service import WeatherService

router = APIRouter()


@router.get(
    "/weather",
    response_model=WeatherDataSchema,
    summary="Get current or forecast weather for coordinates",
)
async def get_weather(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    target_time: Optional[datetime] = Query(None, description="Target forecast ISO timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeatherDataSchema:
    """
    Returns normalized weather data from the active weather provider with Redis caching.
    """
    weather_svc = WeatherService()
    t_time = target_time or datetime.now(timezone.utc)
    weather = await weather_svc.get_forecast(latitude=lat, longitude=lng, target_time=t_time)

    return WeatherDataSchema(
        latitude=weather.latitude,
        longitude=weather.longitude,
        timestamp=weather.timestamp,
        valid_from=weather.valid_from,
        valid_until=weather.valid_until,
        temperature_c=weather.temperature_c,
        precipitation_probability=weather.precipitation_probability,
        precipitation_mm=weather.precipitation_mm,
        condition=weather.condition.value,
        condition_text=weather.condition_text,
        wind_speed_kmh=weather.wind_speed_kmh,
        is_severe=weather.is_severe,
        alerts=[
            {
                "title": a.title,
                "description": a.description,
                "severity": a.severity.value,
                "valid_from": a.valid_from,
                "valid_until": a.valid_until,
                "source": a.source,
                "official_url": a.official_url,
            }
            for a in weather.alerts
        ],
        provider=weather.provider,
        retrieved_at=weather.retrieved_at,
        attribution=weather.attribution,
    )


@router.get(
    "/alarm/{alarm_id}",
    response_model=ContextSummaryResponse,
    summary="Get evaluated context summary (Weather + Calendar) for an alarm",
)
async def get_alarm_context(
    alarm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContextSummaryResponse:
    """
    Evaluates weather along the route/destination and linked calendar events.
    Returns explainable context results and recommendation policies.
    """
    user_id = current_user.id
    context_svc = ContextService(
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
        calendar_repo=CalendarRepository(db),
    )

    results: List[ContextResult] = await context_svc.evaluate_alarm_context(
        alarm_id=alarm_id, user_id=user_id
    )

    has_weather_warning = any(
        r.context_type == ContextType.WEATHER
        and r.finding in {ContextFinding.RAIN_DURING_JOURNEY, ContextFinding.SEVERE_WEATHER_ALERT}
        for r in results
    )
    has_calendar_warning = any(
        r.context_type == ContextType.CALENDAR
        and r.finding in {ContextFinding.CALENDAR_EVENT_TIME_CHANGED, ContextFinding.CALENDAR_EVENT_CANCELLED}
        for r in results
    )

    recommended_buffer = max([r.recommended_buffer_minutes for r in results] or [0])

    response_items = [
        ContextResultResponse(
            context_type=r.context_type.value,
            source=r.source,
            evaluated_at=r.evaluated_at,
            valid_time_window=r.valid_time_window,
            freshness=r.freshness,
            relevance=r.relevance.value,
            finding=r.finding.value,
            recommended_action=r.recommended_action.value,
            recommended_buffer_minutes=r.recommended_buffer_minutes,
            requires_confirmation=r.requires_confirmation,
            explanation=r.explanation,
            policy_version=r.policy_version,
            metadata=r.metadata,
        )
        for r in results
    ]

    return ContextSummaryResponse(
        alarm_id=alarm_id,
        evaluated_at=datetime.now(timezone.utc),
        results=response_items,
        has_weather_warning=has_weather_warning,
        has_calendar_warning=has_calendar_warning,
        recommended_total_buffer=recommended_buffer,
    )


@router.post(
    "/alarm/{alarm_id}/apply-weather-buffer",
    response_model=AlarmResponse,
    summary="Explicitly apply recommended weather buffer to alarm schedule",
)
async def apply_alarm_weather_buffer(
    alarm_id: uuid.UUID,
    payload: ApplyWeatherBufferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlarmResponse:
    """
    Applies user-approved or custom weather buffer.
    Triggers dynamic recalculation using Step 8 engine with optimistic concurrency check.
    """
    user_id = current_user.id
    context_svc = ContextService(
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
        calendar_repo=CalendarRepository(db),
    )

    result = await context_svc.apply_weather_buffer(
        alarm_id=alarm_id,
        user_id=user_id,
        buffer_minutes=payload.buffer_minutes,
        expected_version=payload.expected_version,
    )

    alarm_repo = AlarmRepository(db)
    updated_alarm = alarm_repo.get(alarm_id)
    return AlarmResponse.model_validate(updated_alarm)
