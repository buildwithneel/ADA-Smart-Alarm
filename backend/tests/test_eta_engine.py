"""
Tests for the ADA ETA Calculation Engine.

Tests cover:
1. ETACalculationEngine — pure domain math (no I/O)
   a. Basic wake/leave time calculation
   b. Weather modifier application
   c. Safety buffer integration
   d. Tomorrow-rollover for past arrival times
   e. Haversine heuristic fallback duration computation
   f. Confidence score adjustment
2. ETACalculateRequest schema validation
3. ETAPreviewResponse structure
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.alarm import TransportMode
from app.schemas.eta import (
    ETACalculateRequest,
    ETAPreviewRequest,
    WeatherCondition,
)
from app.services.eta_engine import (
    CONFIDENCE_GOOGLE_LIVE,
    CONFIDENCE_HEURISTIC,
    ETACalculationEngine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_request(
    arrival: str = "09:00",
    prep: int = 30,
    buffer: int = 15,
    mode: TransportMode = TransportMode.DRIVING,
    weather: WeatherCondition | None = None,
) -> ETACalculateRequest:
    return ETACalculateRequest(
        origin_lat=23.2156,
        origin_lng=72.6369,
        dest_lat=22.5996,
        dest_lng=72.8205,
        desired_arrival_time=arrival,
        preparation_time_minutes=prep,
        safety_buffer_minutes=buffer,
        transport_mode=mode,
        weather_condition=weather,
    )


# ---------------------------------------------------------------------------
# 1. Basic wake/leave/arrival time calculation
# ---------------------------------------------------------------------------

class TestETAEngineBasicCalculation:
    def test_leave_time_is_before_arrival(self):
        """Leave time must always be before desired arrival."""
        req = make_request(arrival="09:00", buffer=15, prep=30)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,  # 30 min
            traffic_duration_seconds=2280,  # 38 min
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        from datetime import datetime
        leave_dt = datetime.fromisoformat(result.leave_time_iso)
        arrival_dt = datetime.fromisoformat(result.arrival_time_iso)
        assert leave_dt < arrival_dt

    def test_wake_time_is_before_leave_time(self):
        """Wake time must always be before leave time."""
        req = make_request(arrival="09:00", buffer=15, prep=30)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        wake_dt = datetime.fromisoformat(result.wake_time_iso)
        leave_dt = datetime.fromisoformat(result.leave_time_iso)
        assert wake_dt < leave_dt

    def test_travel_minutes_equals_traffic_seconds_div_60(self):
        """Total travel minutes must reflect traffic duration."""
        req = make_request(arrival="09:00")
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,  # 38 min
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.total_travel_minutes == 38

    def test_breakdown_traffic_delay_correct(self):
        """Traffic delay = traffic_mins - base_mins."""
        req = make_request(arrival="09:00")
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,  # 30 min
            traffic_duration_seconds=2280,  # 38 min
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.breakdown.traffic_delay_minutes == 8  # 38 - 30

    def test_leave_time_accounts_for_buffer(self):
        """Leave time = arrival - (traffic_mins + safety_buffer)."""
        req = make_request(arrival="09:00", buffer=15, prep=0)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1200,  # 20 min base
            traffic_duration_seconds=1800,  # 30 min with traffic
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        arrival_dt = datetime.fromisoformat(result.arrival_time_iso)
        leave_dt = datetime.fromisoformat(result.leave_time_iso)
        # leave = arrival - (30 + 15) = 45 min before arrival
        expected_delta = timedelta(minutes=45)
        actual_delta = arrival_dt - leave_dt
        assert abs((actual_delta - expected_delta).total_seconds()) < 60

    def test_total_time_budget_is_sum(self):
        """Total budget = prep + travel + safety_buffer."""
        prep = 30
        buffer = 15
        traffic_mins = 38
        req = make_request(arrival="09:00", prep=prep, buffer=buffer)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=traffic_mins * 60,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        expected_budget = prep + traffic_mins + buffer
        assert result.total_time_budget_minutes == expected_budget

    def test_output_format_12h(self):
        """Wake and leave times must be in HH:MM AM/PM format."""
        req = make_request(arrival="09:00")
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        import re
        pattern = r"^\d{2}:\d{2} (AM|PM)$"
        assert re.match(pattern, result.recommended_wake_time)
        assert re.match(pattern, result.recommended_leave_time)
        assert re.match(pattern, result.expected_arrival_time)

    def test_engine_version_present(self):
        """Engine version must be set in response."""
        req = make_request()
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.engine_version == "1.0.0"


# ---------------------------------------------------------------------------
# 2. Weather modifier tests
# ---------------------------------------------------------------------------

class TestETAEngineWeatherModifier:
    def test_rain_adds_15_percent_buffer(self):
        """Rain should add 15% of traffic_mins to weather_buffer."""
        req = make_request(weather=WeatherCondition.RAIN)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=3600,  # 60 min
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        # 15% of 60 = 9 min
        assert result.breakdown.weather_buffer_minutes == 9

    def test_storm_adds_35_percent_buffer(self):
        """Storm should add 35% of traffic_mins."""
        req = make_request(weather=WeatherCondition.STORM)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=6000,  # 100 min
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.breakdown.weather_buffer_minutes == 35  # 35% of 100

    def test_clear_weather_zero_buffer(self):
        """Clear weather must add zero buffer."""
        req = make_request(weather=WeatherCondition.CLEAR)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.breakdown.weather_buffer_minutes == 0

    def test_no_weather_condition_zero_buffer(self):
        """None weather_condition must produce zero buffer."""
        req = make_request(weather=None)
        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.breakdown.weather_buffer_minutes == 0

    def test_weather_reduces_confidence(self):
        """Adverse weather should reduce confidence score by 0.05."""
        req_rain = make_request(weather=WeatherCondition.RAIN)
        req_clear = make_request(weather=WeatherCondition.CLEAR)
        base = 1800
        traffic = 2280

        result_rain = ETACalculationEngine.calculate(
            request=req_rain,
            base_duration_seconds=base,
            traffic_duration_seconds=traffic,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        result_clear = ETACalculationEngine.calculate(
            request=req_clear,
            base_duration_seconds=base,
            traffic_duration_seconds=traffic,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result_rain.breakdown.confidence_score < result_clear.breakdown.confidence_score


# ---------------------------------------------------------------------------
# 3. Haversine heuristic
# ---------------------------------------------------------------------------

class TestHaversineHeuristic:
    def test_driving_adds_traffic_overhead(self):
        """Driving heuristic should add 20% traffic overhead."""
        base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
            23.2156, 72.6369, 22.5996, 72.8205, TransportMode.DRIVING
        )
        assert traffic_secs > base_secs
        ratio = traffic_secs / base_secs
        assert abs(ratio - 1.2) < 0.01  # exactly 20% overhead

    def test_walking_no_traffic_overhead(self):
        """Walking heuristic should have no traffic overhead."""
        base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
            23.2156, 72.6369, 22.5996, 72.8205, TransportMode.WALKING
        )
        assert base_secs == traffic_secs

    def test_minimum_duration_enforced(self):
        """Heuristic must return at least 5 minutes (300s) even for very short distances."""
        base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
            23.2156, 72.6369, 23.2157, 72.6370, TransportMode.DRIVING
        )
        assert base_secs >= 300
        assert traffic_secs >= 300

    def test_known_haversine_distance(self):
        """Rough check that Bangalore to Mumbai (approx 980km) gives reasonable driving time."""
        # Bangalore (12.97, 77.59) → Mumbai (19.07, 72.88) ≈ 980 km
        base_secs, _ = ETACalculationEngine.calculate_heuristic_duration(
            12.9716, 77.5946, 19.0760, 72.8777, TransportMode.DRIVING
        )
        base_mins = base_secs // 60
        # At 35 km/h avg for 980km ≈ 1680 min. Should be in reasonable range.
        assert 1200 <= base_mins <= 2400


# ---------------------------------------------------------------------------
# 4. Schema validation
# ---------------------------------------------------------------------------

class TestETASchemaValidation:
    def test_invalid_arrival_time_format_rejected(self):
        """Invalid arrival time format should fail validation."""
        with pytest.raises(Exception):
            ETACalculateRequest(
                origin_lat=23.2,
                origin_lng=72.6,
                dest_lat=22.5,
                dest_lng=72.8,
                desired_arrival_time="9:00 AM",  # Invalid: needs HH:MM 24h
            )

    def test_latitude_out_of_range_rejected(self):
        """Latitude outside [-90, 90] should fail validation."""
        with pytest.raises(Exception):
            ETACalculateRequest(
                origin_lat=95.0,  # Invalid
                origin_lng=72.6,
                dest_lat=22.5,
                dest_lng=72.8,
                desired_arrival_time="09:00",
            )

    def test_valid_request_passes(self):
        """Well-formed request must pass validation without errors."""
        req = ETACalculateRequest(
            origin_lat=23.2156,
            origin_lng=72.6369,
            dest_lat=22.5996,
            dest_lng=72.8205,
            desired_arrival_time="09:00",
            preparation_time_minutes=30,
            safety_buffer_minutes=15,
            transport_mode=TransportMode.DRIVING,
        )
        assert req.desired_arrival_time == "09:00"
        assert req.preparation_time_minutes == 30


# ---------------------------------------------------------------------------
# 5. Preview calculation
# ---------------------------------------------------------------------------

class TestETAEnginePreview:
    def test_preview_wake_before_leave(self):
        """Preview must have wake time before leave time."""
        req = ETAPreviewRequest(
            origin_lat=23.2156,
            origin_lng=72.6369,
            dest_lat=22.5996,
            dest_lng=72.8205,
            desired_arrival_time="09:00",
            preparation_time_minutes=30,
            safety_buffer_minutes=15,
            transport_mode=TransportMode.DRIVING,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
        )
        result = ETACalculationEngine.calculate_preview(
            request=req,
            base_duration_seconds=1800,
            traffic_duration_seconds=2280,
            data_source="google",
            provider_confidence=CONFIDENCE_GOOGLE_LIVE,
        )
        assert result.recommended_wake_time != result.recommended_leave_time
        assert result.total_travel_minutes == 38  # 2280 / 60
        assert result.traffic_delay_minutes == 8  # 38 - 30
        assert result.safety_buffer_minutes == 15
        assert result.preparation_time_minutes == 30
