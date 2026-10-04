"""
ADA ETA Calculation Engine — Pure Domain Layer.

Converts:
  Current Location + Destination + Route Duration + Traffic Duration +
  Preparation Time + Safety Buffer + Required Arrival Time

Into:
  Recommended Wake Time + Recommended Leave Time + Expected Arrival Time +
  Full metadata breakdown

Design principles:
  - Pure computation: no I/O, no external calls
  - Timezone-aware: all calculations anchor on explicit dates
  - Weather-adaptive: applies buffer modifiers for adverse conditions
  - Deterministic: same inputs always produce same outputs
  - Transparent: full breakdown metadata for UI display
  - Version-stamped: engine version in every output
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from app.models.alarm import TransportMode
from app.schemas.eta import (
    ETABreakdown,
    ETACalculateRequest,
    ETACalculateResponse,
    ETAPreviewRequest,
    ETAPreviewResponse,
    WeatherCondition,
)

logger = logging.getLogger("ada.engine.eta")

ENGINE_VERSION = "1.0.0"

# Heuristic speed baselines (km/h) used when no routing provider data available
HEURISTIC_SPEEDS_KMH: dict[TransportMode, float] = {
    TransportMode.DRIVING: 35.0,
    TransportMode.TRANSIT: 25.0,
    TransportMode.BICYCLING: 15.0,
    TransportMode.WALKING: 4.5,
}

# Weather buffer modifiers: percentage of total travel time added
WEATHER_BUFFER_FACTORS: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 0.0,
    WeatherCondition.CLOUDY: 0.0,
    WeatherCondition.RAIN: 0.15,
    WeatherCondition.HEAVY_RAIN: 0.25,
    WeatherCondition.STORM: 0.35,
    WeatherCondition.SNOW: 0.30,
    WeatherCondition.FOG: 0.20,
    WeatherCondition.UNKNOWN: 0.0,
}

# Confidence score reduction per fallback tier
CONFIDENCE_GOOGLE_LIVE: float = 0.97
CONFIDENCE_MAPBOX_LIVE: float = 0.93
CONFIDENCE_HEURISTIC: float = 0.70


class ETACalculationEngine:
    """
    Core domain engine for ADA ETA calculations.

    Responsibilities:
    1. Parse desired arrival time into an absolute UTC datetime
    2. Apply dynamic buffer modifiers (weather, congestion)
    3. Compute leave time = arrival - (travel + buffers)
    4. Compute wake time  = leave  - preparation
    5. Build full metadata breakdown
    6. Format outputs in both human-readable and ISO-8601 formats

    This class performs NO I/O. Routing duration must be provided as inputs.
    """

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    @classmethod
    def calculate(
        cls,
        request: ETACalculateRequest,
        base_duration_seconds: int,
        traffic_duration_seconds: int,
        distance_km: Optional[float] = None,
        data_source: str = "heuristic",
        provider_confidence: float = CONFIDENCE_HEURISTIC,
    ) -> ETACalculateResponse:
        """
        Perform a full ETA calculation given route durations and user parameters.

        Args:
            request: The validated ETACalculateRequest with all user settings.
            base_duration_seconds: Route duration without traffic (from routing provider).
            traffic_duration_seconds: Traffic-aware route duration (from routing provider).
            distance_km: Optional distance for display in breakdown.
            data_source: Which provider/method produced the durations.
            provider_confidence: Starting confidence for this data source.

        Returns:
            ETACalculateResponse with wake, leave, and arrival times plus full breakdown.
        """
        # 1. Parse arrival time into datetime
        arrival_dt = cls._parse_arrival_datetime(
            request.desired_arrival_time, request.target_date_iso
        )

        # 2. Compute travel times
        base_travel_mins = max(1, base_duration_seconds // 60)
        traffic_mins = max(1, traffic_duration_seconds // 60)
        traffic_delay_mins = max(0, traffic_mins - base_travel_mins)

        # 3. Apply weather buffer modifier
        weather_buffer_mins, weather_label = cls._apply_weather_modifier(
            request.weather_condition, traffic_mins
        )

        # 4. Total commute budget (travel + user safety buffer + weather modifier)
        total_travel_with_buffer_mins = (
            traffic_mins + request.safety_buffer_minutes + weather_buffer_mins
        )

        # 5. Compute leave time
        leave_dt = arrival_dt - timedelta(minutes=total_travel_with_buffer_mins)

        # 6. Compute wake time
        wake_dt = leave_dt - timedelta(minutes=request.preparation_time_minutes)

        # 7. Compute planned arrival time (arrival minus safety and weather buffers = leave + traffic)
        planned_arrival_dt = leave_dt + timedelta(minutes=traffic_mins)

        # 8. Total budget from wake to arrival
        total_budget_mins = (
            total_travel_with_buffer_mins + request.preparation_time_minutes
        )

        # 9. Compute confidence (reduce slightly for weather uncertainty)
        if weather_buffer_mins > 0:
            provider_confidence = max(0.5, provider_confidence - 0.05)

        # 10. Build breakdown
        breakdown = ETABreakdown(
            base_travel_minutes=base_travel_mins,
            traffic_duration_minutes=traffic_mins,
            traffic_delay_minutes=traffic_delay_mins,
            distance_km=distance_km,
            safety_buffer_minutes=request.safety_buffer_minutes,
            weather_buffer_minutes=weather_buffer_mins,
            total_travel_with_buffer_minutes=total_travel_with_buffer_mins,
            preparation_time_minutes=request.preparation_time_minutes,
            weather_condition=weather_label,
            data_source=data_source,
            confidence_score=round(provider_confidence, 4),
        )

        # 11. Format output
        now_iso = datetime.now(tz=timezone.utc).isoformat()

        return ETACalculateResponse(
            recommended_wake_time=cls._format_12h(wake_dt),
            recommended_leave_time=cls._format_12h(leave_dt),
            expected_arrival_time=cls._format_12h(arrival_dt),
            planned_arrival_time=cls._format_12h(planned_arrival_dt),
            wake_time_iso=wake_dt.isoformat(),
            leave_time_iso=leave_dt.isoformat(),
            arrival_time_iso=arrival_dt.isoformat(),
            planned_arrival_time_iso=planned_arrival_dt.isoformat(),
            total_travel_minutes=traffic_mins,
            total_time_budget_minutes=total_budget_mins,
            breakdown=breakdown,
            calculation_timestamp=now_iso,
            engine_version=ENGINE_VERSION,
        )

    @classmethod
    def calculate_preview(
        cls,
        request: ETAPreviewRequest,
        base_duration_seconds: int,
        traffic_duration_seconds: int,
        data_source: str = "heuristic",
        provider_confidence: float = CONFIDENCE_HEURISTIC,
    ) -> ETAPreviewResponse:
        """
        Lightweight ETA preview calculation for live UI updates.
        Same math as calculate() but returns a minimal response payload.
        """
        arrival_dt = cls._parse_arrival_datetime(request.desired_arrival_time, None)

        base_travel_mins = max(1, base_duration_seconds // 60)
        traffic_mins = max(1, traffic_duration_seconds // 60)
        traffic_delay_mins = max(0, traffic_mins - base_travel_mins)

        total_travel_with_buffer_mins = (
            traffic_mins + request.safety_buffer_minutes
        )

        leave_dt = arrival_dt - timedelta(minutes=total_travel_with_buffer_mins)
        wake_dt = leave_dt - timedelta(minutes=request.preparation_time_minutes)
        planned_arrival_dt = leave_dt + timedelta(minutes=traffic_mins)

        total_budget = total_travel_with_buffer_mins + request.preparation_time_minutes

        return ETAPreviewResponse(
            recommended_wake_time=cls._format_12h(wake_dt),
            recommended_leave_time=cls._format_12h(leave_dt),
            expected_arrival_time=cls._format_12h(arrival_dt),
            planned_arrival_time=cls._format_12h(planned_arrival_dt),
            total_travel_minutes=traffic_mins,
            traffic_delay_minutes=traffic_delay_mins,
            preparation_time_minutes=request.preparation_time_minutes,
            safety_buffer_minutes=request.safety_buffer_minutes,
            total_budget_minutes=total_budget,
            data_source=data_source,
            confidence_score=round(provider_confidence, 4),
        )

    @classmethod
    def calculate_heuristic_duration(
        cls,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TransportMode,
    ) -> Tuple[int, int]:
        """
        Compute heuristic base and traffic durations using Haversine distance.
        Used as a fallback when no routing provider is available.

        Returns:
            (base_duration_seconds, traffic_duration_seconds)
        """
        distance_km = cls._haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
        speed_kmh = HEURISTIC_SPEEDS_KMH.get(mode, 35.0)

        base_secs = max(300, int((distance_km / speed_kmh) * 3600))

        # Simulate traffic overhead for driving (20% extra)
        if mode == TransportMode.DRIVING:
            traffic_secs = int(base_secs * 1.20)
        else:
            traffic_secs = base_secs

        return base_secs, traffic_secs

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _parse_arrival_datetime(
        arrival_time_str: str, target_date_iso: Optional[str] = None
    ) -> datetime:
        """
        Parse a 'HH:MM' string into a timezone-aware datetime on the target date.
        Defaults to today's local date when target_date_iso is not provided.

        Raises:
            ValueError: If the time or date string is malformed.
        """
        try:
            h, m = (int(p) for p in arrival_time_str.split(":"))
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid desired_arrival_time format '{arrival_time_str}'. Expected HH:MM."
            ) from exc

        if target_date_iso:
            base = datetime.fromisoformat(target_date_iso)
            anchor = base.replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            now = datetime.now()
            anchor = now.replace(hour=h, minute=m, second=0, microsecond=0)
            # If the desired arrival time is earlier than now (by > 1 hour), assume tomorrow
            if anchor < now - timedelta(hours=1):
                anchor += timedelta(days=1)

        return anchor

    @staticmethod
    def _apply_weather_modifier(
        condition: Optional[WeatherCondition], traffic_mins: int
    ) -> Tuple[int, Optional[str]]:
        """
        Compute additional minutes to add based on weather condition.

        Handles both WeatherCondition enum instances and plain string values
        (Pydantic may deserialize enum fields as strings in some configurations).

        Returns:
            (extra_minutes, condition_label)
        """
        if condition is None:
            return 0, None

        # Normalise to string value regardless of whether it's enum or str
        condition_str: str = condition.value if hasattr(condition, "value") else str(condition)

        if condition_str in ("clear", "cloudy", "unknown"):
            return 0, None

        try:
            condition_enum = WeatherCondition(condition_str)
        except ValueError:
            return 0, None

        factor = WEATHER_BUFFER_FACTORS.get(condition_enum, 0.0)
        extra = int(traffic_mins * factor)
        return extra, condition_str

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Compute great-circle distance between two GPS points in kilometres.
        """
        import math
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _format_12h(dt: datetime) -> str:
        """
        Format a datetime into 'HH:MM AM/PM' 12-hour notation.
        Example: datetime(hour=8, minute=7) → '08:07 AM'
        """
        hour = dt.hour
        minute = dt.minute
        period = "AM" if hour < 12 else "PM"
        h12 = hour % 12 or 12
        return f"{h12:02d}:{minute:02d} {period}"
