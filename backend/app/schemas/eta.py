"""
ETA Calculation Engine schemas.

Defines the request and response contracts for the core ADA ETA domain service.
These types decouple the API surface from the internal calculation internals
and allow the engine to evolve (e.g. adding ML predictions) without breaking contracts.
"""

from __future__ import annotations

import enum
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.models.alarm import TransportMode
from app.schemas.base import BaseSchema


class WeatherCondition(str, enum.Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# ETA Calculation Request
# ---------------------------------------------------------------------------

class ETACalculateRequest(BaseSchema):
    """
    Input contract for the ETA Calculation Engine.
    All fields with defaults are optional to enable partial/lightweight previews.
    """

    # Origin coordinates (user's current or saved location)
    origin_lat: float = Field(..., ge=-90.0, le=90.0, description="Origin latitude")
    origin_lng: float = Field(..., ge=-180.0, le=180.0, description="Origin longitude")

    # Destination coordinates
    dest_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination latitude")
    dest_lng: float = Field(..., ge=-180.0, le=180.0, description="Destination longitude")

    # Required arrival parameters
    desired_arrival_time: str = Field(
        ...,
        description="Target arrival time in 24h HH:MM format, e.g. '09:00'",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )

    # Preparation and safety time
    preparation_time_minutes: int = Field(
        default=30, ge=0, le=360,
        description="User's morning routine / preparation time in minutes",
    )
    safety_buffer_minutes: int = Field(
        default=15, ge=0, le=180,
        description="Explicit safety traffic buffer to add to leave time",
    )

    # Transport mode
    transport_mode: TransportMode = Field(
        default=TransportMode.DRIVING,
        description="Mode of transport for route calculation",
    )

    # Optional travel duration override (when already calculated)
    override_base_duration_seconds: Optional[int] = Field(
        None, ge=0,
        description="Pre-computed base route duration in seconds. Skips route API call when provided.",
    )
    override_traffic_duration_seconds: Optional[int] = Field(
        None, ge=0,
        description="Pre-computed traffic-adjusted route duration in seconds.",
    )

    # Optional context for weather modifier
    weather_condition: Optional[WeatherCondition] = Field(
        None,
        description="Current weather condition at origin for dynamic buffer modifier",
    )

    # Optional departure date (defaults to today's date)
    target_date_iso: Optional[str] = Field(
        None,
        description="ISO-8601 date string (YYYY-MM-DD). Defaults to today's local date.",
    )


# ---------------------------------------------------------------------------
# ETA Calculation Metadata  (internal breakdown)
# ---------------------------------------------------------------------------

class ETABreakdown(BaseSchema):
    """
    Detailed breakdown of how the ETA was calculated.
    Provides full transparency for debugging and UI display.
    """

    # Route data
    base_travel_minutes: int = Field(..., description="Route duration without traffic (minutes)")
    traffic_duration_minutes: int = Field(..., description="Route duration with live traffic (minutes)")
    traffic_delay_minutes: int = Field(..., ge=0, description="Extra minutes due to traffic congestion")
    distance_km: Optional[float] = Field(None, description="Route distance in kilometres")

    # Safety / dynamic modifiers applied
    safety_buffer_minutes: int = Field(..., description="Explicit safety buffer applied")
    weather_buffer_minutes: int = Field(default=0, ge=0, description="Additional minutes added due to adverse weather")
    total_travel_with_buffer_minutes: int = Field(..., description="Total commute budget (travel + all buffers)")

    # Preparation
    preparation_time_minutes: int = Field(..., description="Morning routine / preparation time")

    # Confidence
    weather_condition: Optional[str] = Field(None, description="Weather condition that triggered modifier")
    data_source: str = Field(..., description="Which routing provider resolved the route")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the calculation [0.0-1.0]")


class ETACalculateResponse(BaseSchema):
    """
    Full ETA calculation response from the ADA ETA Calculation Engine.
    """

    # Core outputs — the primary display values
    recommended_wake_time: str = Field(..., description="Wake time in HH:MM 12h format")
    recommended_leave_time: str = Field(..., description="Leave home time in HH:MM 12h format")
    expected_arrival_time: str = Field(..., description="Arrival time echoed back in HH:MM 12h format")
    planned_arrival_time: Optional[str] = Field(None, description="Planned arrival time at destination (HH:MM 12h format)")

    # ISO-8601 datetime representations for machine consumption
    wake_time_iso: str = Field(..., description="Wake time as ISO-8601 datetime")
    leave_time_iso: str = Field(..., description="Leave time as ISO-8601 datetime")
    arrival_time_iso: str = Field(..., description="Arrival time as ISO-8601 datetime")
    planned_arrival_time_iso: Optional[str] = Field(None, description="Planned arrival time as ISO-8601 datetime")

    # Trip summary
    total_travel_minutes: int = Field(..., description="Total travel time including traffic (minutes)")
    total_time_budget_minutes: int = Field(..., description="Total time from wake to arrival (minutes)")

    # Detailed breakdown
    breakdown: ETABreakdown

    # Metadata
    calculation_timestamp: str = Field(..., description="When this calculation was performed (ISO-8601)")
    engine_version: str = Field(default="1.0.0", description="ETA Engine version that produced this result")


# ---------------------------------------------------------------------------
# ETA Preview (lightweight — for live form preview without storing)
# ---------------------------------------------------------------------------

class ETAPreviewRequest(BaseSchema):
    """
    Lightweight preview request. Does not require auth.
    Used for the live dynamic preview panel in CreateAlarmPage.
    """
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lng: float = Field(..., ge=-180.0, le=180.0)
    dest_lat: float = Field(..., ge=-90.0, le=90.0)
    dest_lng: float = Field(..., ge=-180.0, le=180.0)
    desired_arrival_time: str = Field(..., pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    preparation_time_minutes: int = Field(default=30, ge=0, le=360)
    safety_buffer_minutes: int = Field(default=15, ge=0, le=180)
    transport_mode: TransportMode = Field(default=TransportMode.DRIVING)
    # If client already computed route, pass durations to skip extra API call
    base_duration_seconds: Optional[int] = Field(None, ge=0)
    traffic_duration_seconds: Optional[int] = Field(None, ge=0)


class ETAPreviewResponse(BaseSchema):
    """
    Lightweight ETA preview for form live-update use case.
    Does not include full breakdown to minimize payload size.
    """
    recommended_wake_time: str
    recommended_leave_time: str
    expected_arrival_time: str
    planned_arrival_time: Optional[str] = None

    # Time deltas for quick display
    total_travel_minutes: int
    traffic_delay_minutes: int
    preparation_time_minutes: int
    safety_buffer_minutes: int
    total_budget_minutes: int

    # Optional summary text
    data_source: str
    confidence_score: float


# ---------------------------------------------------------------------------
# Alarm ETA Re-evaluation (for persisting calculated times back to Alarm model)
# ---------------------------------------------------------------------------

class AlarmETAUpdateResult(BaseSchema):
    """
    Result returned when a specific alarm's ETA is recalculated and persisted.
    Mirrors AlarmResponse calculated fields for frontend sync.
    """
    alarm_id: str
    calculated_wake_time: Optional[datetime]
    calculated_leave_time: Optional[datetime]
    current_travel_minutes: int
    traffic_delay_minutes: int
    last_evaluated_at: datetime
    confidence_score: float
