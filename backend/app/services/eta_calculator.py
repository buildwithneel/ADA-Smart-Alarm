import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx

from app.core.config import settings
from app.models.alarm import TransportMode
from app.schemas.alarm import AlarmCalculateResult


class ETACalculatorService:
    """
    Core Domain Service responsible for calculating dynamic travel times,
    traffic delay buffers, leave times, and wake-up times for ADA alarms.
    """

    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def haversine_distance_km(
        cls, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Computes great-circle distance between two GPS coordinates in kilometers.
        Used as high-speed fallback and sanity check validation.
        """
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return cls.EARTH_RADIUS_KM * c

    @classmethod
    async def fetch_google_routes_eta(
        cls,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TransportMode,
    ) -> Tuple[int, int]:
        """
        Calls Google Directions / Distance Matrix API to get real-time duration
        and traffic delay in minutes. Returns (normal_duration_mins, traffic_delay_mins).
        """
        if not settings.GOOGLE_MAPS_API_KEY:
            # Deterministic fallback calculation when API key is not yet set
            distance_km = cls.haversine_distance_km(
                origin_lat, origin_lng, dest_lat, dest_lng
            )
            speed_kmh = {
                TransportMode.DRIVING: 35.0,
                TransportMode.TRANSIT: 25.0,
                TransportMode.BICYCLING: 15.0,
                TransportMode.WALKING: 4.5,
            }.get(mode, 35.0)

            base_minutes = max(5, int((distance_km / speed_kmh) * 60))
            # Simulated traffic delay if driving in daytime
            traffic_delay = (
                int(base_minutes * 0.2) if mode == TransportMode.DRIVING else 0
            )
            return base_minutes, traffic_delay

        # Google Maps Directions API request
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "mode": mode.value,
            "departure_time": "now",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes"):
                    leg = data["routes"][0]["legs"][0]
                    duration_sec = leg.get("duration", {}).get("value", 1800)
                    duration_traffic_sec = leg.get("duration_in_traffic", {}).get(
                        "value", duration_sec
                    )

                    duration_mins = max(1, duration_sec // 60)
                    traffic_delay = max(0, (duration_traffic_sec - duration_sec) // 60)
                    return duration_mins, traffic_delay

        # Fallback if request fails
        dist = cls.haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
        return max(5, int(dist * 2)), 5

    @classmethod
    async def calculate_alarm_schedule(
        cls,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        desired_arrival_time_str: str,  # "HH:MM" e.g. "09:00"
        routine_minutes: int,
        buffer_minutes: int,
        transport_mode: TransportMode = TransportMode.DRIVING,
        weather_condition: Optional[str] = None,
    ) -> AlarmCalculateResult:
        """
        Executes ADA's core dynamic calculation formula:
        1. Travel Minutes + Traffic Delay from Google Maps.
        2. Weather buffer modifier (+15% if rainy/snowy).
        3. Leave Time = Arrival Time - (Travel Minutes + Dynamic Buffer).
        4. Wake Time = Leave Time - Routine Minutes.
        """
        base_travel, traffic_delay = await cls.fetch_google_routes_eta(
            origin_lat, origin_lng, dest_lat, dest_lng, transport_mode
        )

        total_travel = base_travel + traffic_delay

        # Weather modifier
        dynamic_buffer = buffer_minutes
        if weather_condition and any(
            w in weather_condition.lower() for w in ["rain", "storm", "snow", "fog"]
        ):
            dynamic_buffer += int(total_travel * 0.15)  # 15% weather safety cushion

        # Parse desired arrival
        parts = desired_arrival_time_str.split(":")
        arrival_hour = int(parts[0])
        arrival_minute = int(parts[1]) if len(parts) > 1 else 0

        # Anchor onto today's date for precise timedelta subtraction
        now = datetime.now()
        arrival_dt = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=arrival_hour,
            minute=arrival_minute,
        )

        # Leave Time = Desired Arrival - Travel - Buffer
        total_commute_budget = timedelta(minutes=total_travel + dynamic_buffer)
        leave_dt = arrival_dt - total_commute_budget

        # Wake Time = Leave Time - Morning Routine
        routine_budget = timedelta(minutes=routine_minutes)
        wake_dt = leave_dt - routine_budget

        return AlarmCalculateResult(
            travel_minutes=total_travel,
            traffic_delay_minutes=traffic_delay,
            recommended_leave_time=leave_dt.strftime("%I:%M %p"),
            recommended_wake_time=wake_dt.strftime("%I:%M %p"),
            weather_summary=weather_condition or "Clear",
            confidence_score=0.95 if settings.GOOGLE_MAPS_API_KEY else 0.80,
        )
