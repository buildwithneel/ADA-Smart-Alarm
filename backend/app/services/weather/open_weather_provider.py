from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.weather.base import (
    WeatherAlert,
    WeatherAlertSeverity,
    WeatherCondition,
    WeatherData,
    WeatherProvider,
)

logger = logging.getLogger("ada.weather.openweather")


class OpenWeatherMapProvider(WeatherProvider):
    """
    OpenWeatherMap 5-day / 3-hour forecast provider.
    Activated when WEATHER_PROVIDER="openweathermap" and WEATHER_API_KEY is configured.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
    CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.WEATHER_API_KEY

    @property
    def provider_name(self) -> str:
        return "openweathermap"

    @property
    def attribution(self) -> str:
        return "Weather data provided by OpenWeatherMap"

    def _map_condition(self, main: str, description: str, weather_id: int) -> tuple[WeatherCondition, bool]:
        main_lower = main.lower()
        if 200 <= weather_id < 300:
            return WeatherCondition.THUNDERSTORM, True
        elif 300 <= weather_id < 400 or 500 <= weather_id < 510:
            return WeatherCondition.RAIN, False
        elif 511 <= weather_id < 600:
            return WeatherCondition.HEAVY_RAIN, True
        elif 600 <= weather_id < 700:
            return WeatherCondition.SNOW, False
        elif 700 <= weather_id < 800:
            return WeatherCondition.FOG, False
        elif weather_id == 800:
            return WeatherCondition.CLEAR, False
        elif 801 <= weather_id < 900:
            return WeatherCondition.CLOUDY, False
        return WeatherCondition.UNKNOWN, False

    async def get_forecast(
        self, latitude: float, longitude: float, target_time: datetime
    ) -> WeatherData:
        if not self.api_key:
            raise RuntimeError("OpenWeatherMap API key not configured")

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                res = await client.get(self.BASE_URL, params=params)
                if res.status_code != 200:
                    raise RuntimeError(f"OpenWeatherMap API error {res.status_code}: {res.text}")

                data = res.json()
                return self._parse_forecast_list(data, latitude, longitude, target_time)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise RuntimeError(f"OpenWeatherMap request failed: {exc}") from exc

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> WeatherData:
        if not self.api_key:
            raise RuntimeError("OpenWeatherMap API key not configured")

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                res = await client.get(self.CURRENT_URL, params=params)
                if res.status_code != 200:
                    raise RuntimeError(f"OpenWeatherMap API error: {res.status_code}")

                d = res.json()
                now = datetime.now(timezone.utc)
                weather_item = (d.get("weather") or [{}])[0]
                cond, is_sev = self._map_condition(
                    weather_item.get("main", ""),
                    weather_item.get("description", ""),
                    weather_item.get("id", 800),
                )

                return WeatherData(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=now,
                    valid_from=now - timedelta(minutes=30),
                    valid_until=now + timedelta(minutes=30),
                    temperature_c=d.get("main", {}).get("temp"),
                    precipitation_probability=None,
                    precipitation_mm=d.get("rain", {}).get("1h", 0.0),
                    condition=cond,
                    condition_text=weather_item.get("description", "Clear").capitalize(),
                    wind_speed_kmh=d.get("wind", {}).get("speed", 0.0) * 3.6 if d.get("wind", {}).get("speed") is not None else None,
                    is_severe=is_sev,
                    alerts=[],
                    provider=self.provider_name,
                    retrieved_at=now,
                    attribution=self.attribution,
                )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise RuntimeError(f"OpenWeatherMap current weather failed: {exc}") from exc

    def _parse_forecast_list(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        target_time: datetime,
    ) -> WeatherData:
        now = datetime.now(timezone.utc)
        items = data.get("list", [])
        target_utc = target_time.astimezone(timezone.utc) if target_time.tzinfo else target_time.replace(tzinfo=timezone.utc)

        best_item = items[0] if items else {}
        min_diff = float("inf")
        for item in items:
            dt = datetime.fromtimestamp(item.get("dt", 0), tz=timezone.utc)
            diff = abs((dt - target_utc).total_seconds())
            if diff < min_diff:
                min_diff = diff
                best_item = item

        weather_item = (best_item.get("weather") or [{}])[0]
        cond, is_sev = self._map_condition(
            weather_item.get("main", ""),
            weather_item.get("description", ""),
            weather_item.get("id", 800),
        )
        item_dt = datetime.fromtimestamp(best_item.get("dt", int(now.timestamp())), tz=timezone.utc)

        rain_val = best_item.get("rain", {}).get("3h", 0.0)
        precip_prob = int((best_item.get("pop", 0.0) or 0.0) * 100)

        alerts: list[WeatherAlert] = []
        if is_sev:
            alerts.append(
                WeatherAlert(
                    title=f"Severe Weather: {weather_item.get('main', 'Alert')}",
                    description=weather_item.get("description", ""),
                    severity=WeatherAlertSeverity.SEVERE if cond == WeatherCondition.THUNDERSTORM else WeatherAlertSeverity.MODERATE,
                    valid_from=item_dt - timedelta(hours=1),
                    valid_until=item_dt + timedelta(hours=2),
                    source="OpenWeatherMap",
                    official_url="https://openweathermap.org",
                )
            )

        return WeatherData(
            latitude=latitude,
            longitude=longitude,
            timestamp=item_dt,
            valid_from=item_dt - timedelta(hours=1, minutes=30),
            valid_until=item_dt + timedelta(hours=1, minutes=30),
            temperature_c=best_item.get("main", {}).get("temp"),
            precipitation_probability=precip_prob,
            precipitation_mm=float(rain_val),
            condition=cond,
            condition_text=weather_item.get("description", "Clear").capitalize(),
            wind_speed_kmh=best_item.get("wind", {}).get("speed", 0.0) * 3.6 if best_item.get("wind", {}).get("speed") is not None else None,
            is_severe=is_sev or bool(alerts),
            alerts=alerts,
            provider=self.provider_name,
            retrieved_at=now,
            attribution=self.attribution,
        )
