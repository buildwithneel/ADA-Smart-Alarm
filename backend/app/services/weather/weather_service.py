from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.core.config import settings
from app.core.redis import get_redis_client
from app.services.weather.base import (
    WeatherAlert,
    WeatherCondition,
    WeatherData,
    WeatherProvider,
)
from app.services.weather.open_meteo_provider import OpenMeteoWeatherProvider
from app.services.weather.open_weather_provider import OpenWeatherMapProvider

logger = logging.getLogger("ada.services.weather")

# In-memory fallback cache when Redis is unavailable (e.g., local tests)
_in_memory_weather_cache: dict[str, tuple[float, str]] = {}


def clear_weather_cache() -> None:
    """Utility to clear the local in-memory weather fallback cache."""
    _in_memory_weather_cache.clear()


@dataclass
class JourneyWeatherSummary:
    has_precipitation: bool
    is_severe: bool
    condition: WeatherCondition
    condition_text: str
    precipitation_mm: Optional[float]
    temperature_c: Optional[float]
    is_stale: bool
    alerts: List[WeatherAlert] = field(default_factory=list)
    primary_weather: Optional[WeatherData] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    explanation: str = ""
    provider: str = "open-meteo"
    attribution: str = ""


class WeatherService:
    """
    Step 10 Weather Domain Service.
    Coordinates:
    1. Provider abstraction (Open-Meteo default, OpenWeatherMap option).
    2. Redis distributed caching with privacy-preserving rounded coordinates.
    3. Journey-level weather evaluation (origin, destination, time window).
    4. Freshness and data staleness enforcement.
    """

    def __init__(self, provider: Optional[WeatherProvider] = None):
        if provider:
            self.provider = provider
        elif settings.WEATHER_PROVIDER == "openweathermap" and settings.WEATHER_API_KEY:
            self.provider = OpenWeatherMapProvider()
        else:
            self.provider = OpenMeteoWeatherProvider()

    def _build_cache_key(self, lat: float, lng: float, target_time: datetime) -> str:
        # Rounded to 3 decimal places (~110m) to group nearby queries and protect exact locations
        # Time bucketed to the target hour
        target_utc = target_time.astimezone(timezone.utc) if target_time.tzinfo else target_time.replace(tzinfo=timezone.utc)
        hour_bucket = target_utc.strftime("%Y%m%d%H")
        return f"ada:weather:{self.provider.provider_name}:{round(lat, 3)}:{round(lng, 3)}:{hour_bucket}"

    async def _get_cached_weather(self, key: str) -> Optional[WeatherData]:
        try:
            redis_client = get_redis_client()
            raw = redis_client.get(key)
            if raw:
                data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                return WeatherData.model_validate(data)
        except Exception:
            # Fallback to in-memory cache
            entry = _in_memory_weather_cache.get(key)
            if entry:
                expires_at, payload = entry
                if datetime.now(timezone.utc).timestamp() < expires_at:
                    return WeatherData.model_validate(json.loads(payload))
                _in_memory_weather_cache.pop(key, None)
        return None

    async def _set_cached_weather(self, key: str, weather: WeatherData) -> None:
        payload = weather.model_dump_json()
        ttl = settings.WEATHER_CACHE_TTL_SECONDS
        try:
            redis_client = get_redis_client()
            redis_client.set(key, payload, ex=ttl)
        except Exception:
            # Fallback to in-memory cache
            expires_at = datetime.now(timezone.utc).timestamp() + ttl
            _in_memory_weather_cache[key] = (expires_at, payload)

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        target_time: datetime,
        force_refresh: bool = False,
    ) -> WeatherData:
        """
        Gets forecast for coordinates and target time with Redis caching.
        """
        cache_key = self._build_cache_key(latitude, longitude, target_time)
        if not force_refresh:
            cached = await self._get_cached_weather(cache_key)
            if cached:
                logger.debug(f"Weather cache hit for {cache_key}")
                return cached

        logger.info(f"Fetching fresh weather from {self.provider.provider_name} for ({latitude}, {longitude})")
        weather = await self.provider.get_forecast(latitude, longitude, target_time)
        await self._set_cached_weather(cache_key, weather)
        return weather

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> WeatherData:
        """
        Retrieves current conditions.
        """
        return await self.provider.get_current_weather(latitude, longitude)

    async def evaluate_journey_weather(
        self,
        origin_lat: Optional[float],
        origin_lng: Optional[float],
        dest_lat: float,
        dest_lng: float,
        leave_time: datetime,
        arrival_time: datetime,
    ) -> JourneyWeatherSummary:
        """
        Evaluates weather conditions relevant to the planned journey.
        Checks destination conditions at planned arrival, and origin at departure.
        Avoids excessive calls while respecting rate limits.
        """
        now = datetime.now(timezone.utc)
        dest_weather = await self.get_forecast(dest_lat, dest_lng, arrival_time)

        # Check freshness
        age_seconds = (now - dest_weather.retrieved_at).total_seconds()
        is_stale = age_seconds > settings.WEATHER_FORECAST_MAX_AGE_SECONDS

        # Check if origin is far enough to warrant a second check
        origin_weather: Optional[WeatherData] = None
        if origin_lat is not None and origin_lng is not None:
            # Simple threshold: if > 0.1 degree apart (~11 km), evaluate origin departure weather
            if abs(origin_lat - dest_lat) > 0.1 or abs(origin_lng - dest_lng) > 0.1:
                try:
                    origin_weather = await self.get_forecast(origin_lat, origin_lng, leave_time)
                except Exception as exc:
                    logger.warning(f"Could not fetch origin weather: {exc}")

        # Determine qualifying conditions
        all_weathers = [dest_weather]
        if origin_weather:
            all_weathers.append(origin_weather)

        qualifying_rain_conditions = {
            WeatherCondition.RAIN,
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORM,
            WeatherCondition.SNOW,
        }

        has_precip = any(
            (w.condition in qualifying_rain_conditions)
            or ((w.precipitation_mm or 0.0) >= settings.WEATHER_PRECIPITATION_THRESHOLD_MM)
            for w in all_weathers
        )

        is_severe = any(w.is_severe or bool(w.alerts) for w in all_weathers)

        all_alerts: list[WeatherAlert] = []
        for w in all_weathers:
            all_alerts.extend(w.alerts)

        # Primary condition comes from destination
        primary_w = dest_weather
        condition = primary_w.condition
        condition_text = primary_w.condition_text
        precip_mm = primary_w.precipitation_mm
        temp_c = primary_w.temperature_c

        # Compose explainable text
        if is_severe:
            explanation = f"Severe weather detected: {condition_text}. Caution advised for planned journey."
        elif has_precip:
            explanation = f"{condition_text} expected during journey. Travel conditions may be affected."
        else:
            explanation = f"{condition_text} conditions expected during journey."

        if is_stale:
            explanation += " (Weather data may be outdated)."

        return JourneyWeatherSummary(
            has_precipitation=has_precip,
            is_severe=is_severe,
            condition=condition,
            condition_text=condition_text,
            precipitation_mm=precip_mm,
            temperature_c=temp_c,
            is_stale=is_stale,
            alerts=all_alerts,
            primary_weather=primary_w,
            evaluated_at=now,
            explanation=explanation,
            provider=primary_w.provider,
            attribution=primary_w.attribution,
        )
