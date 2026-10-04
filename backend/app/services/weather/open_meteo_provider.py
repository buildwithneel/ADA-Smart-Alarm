from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings
from app.services.weather.base import (
    WeatherAlert,
    WeatherAlertSeverity,
    WeatherCondition,
    WeatherData,
    WeatherProvider,
)

logger = logging.getLogger("ada.weather.open_meteo")

WMO_CODE_MAP: Dict[int, Tuple[WeatherCondition, str, bool]] = {
    0: (WeatherCondition.CLEAR, "Clear sky", False),
    1: (WeatherCondition.CLOUDY, "Mainly clear", False),
    2: (WeatherCondition.CLOUDY, "Partly cloudy", False),
    3: (WeatherCondition.CLOUDY, "Overcast", False),
    45: (WeatherCondition.FOG, "Fog", False),
    48: (WeatherCondition.FOG, "Depositing rime fog", False),
    51: (WeatherCondition.RAIN, "Light drizzle", False),
    53: (WeatherCondition.RAIN, "Moderate drizzle", False),
    55: (WeatherCondition.RAIN, "Dense drizzle", False),
    56: (WeatherCondition.RAIN, "Light freezing drizzle", False),
    57: (WeatherCondition.RAIN, "Dense freezing drizzle", False),
    61: (WeatherCondition.RAIN, "Slight rain", False),
    63: (WeatherCondition.RAIN, "Moderate rain", False),
    65: (WeatherCondition.HEAVY_RAIN, "Heavy rain", False),
    66: (WeatherCondition.HEAVY_RAIN, "Light freezing rain", False),
    67: (WeatherCondition.HEAVY_RAIN, "Heavy freezing rain", False),
    71: (WeatherCondition.SNOW, "Slight snow fall", False),
    73: (WeatherCondition.SNOW, "Moderate snow fall", False),
    75: (WeatherCondition.SNOW, "Heavy snow fall", False),
    77: (WeatherCondition.SNOW, "Snow grains", False),
    80: (WeatherCondition.RAIN, "Slight rain showers", False),
    81: (WeatherCondition.RAIN, "Moderate rain showers", False),
    82: (WeatherCondition.HEAVY_RAIN, "Violent rain showers", True),
    85: (WeatherCondition.SNOW, "Slight snow showers", False),
    86: (WeatherCondition.SNOW, "Heavy snow showers", False),
    95: (WeatherCondition.THUNDERSTORM, "Thunderstorm", True),
    96: (WeatherCondition.THUNDERSTORM, "Thunderstorm with slight hail", True),
    99: (WeatherCondition.THUNDERSTORM, "Thunderstorm with heavy hail", True),
}


class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Open-Meteo weather provider adapter.
    Reliable, open-access, zero-API-key default provider supporting hourly forecasts.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    @property
    def attribution(self) -> str:
        return "Weather data by Open-Meteo.com under CC BY 4.0"

    def _map_wmo_code(self, code: Optional[int]) -> Tuple[WeatherCondition, str, bool]:
        if code is None:
            return WeatherCondition.UNKNOWN, "Unknown conditions", False
        return WMO_CODE_MAP.get(
            code, (WeatherCondition.CLOUDY, f"Code {code}", False)
        )

    async def get_forecast(
        self, latitude: float, longitude: float, target_time: datetime
    ) -> WeatherData:
        """
        Retrieves hourly weather forecast from Open-Meteo and extracts
        the forecast slot closest to target_time.
        """
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "hourly": "temperature_2m,precipitation_probability,precipitation,weathercode,windspeed_10m",
            "current_weather": "true",
            "timezone": "UTC",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    logger.error(
                        f"Open-Meteo returned status {response.status_code}: {response.text}"
                    )
                    raise RuntimeError(f"Open-Meteo API error: {response.status_code}")

                data = response.json()
                return self._parse_hourly_data(data, latitude, longitude, target_time)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Open-Meteo request failed: {exc}")
            raise RuntimeError(f"Open-Meteo service unreachable: {exc}") from exc

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> WeatherData:
        """
        Retrieves current conditions from Open-Meteo.
        """
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current_weather": "true",
            "timezone": "UTC",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    raise RuntimeError(f"Open-Meteo API error: {response.status_code}")

                data = response.json()
                current = data.get("current_weather", {})
                wcode = current.get("weathercode")
                cond, text, is_sev = self._map_wmo_code(wcode)

                now = datetime.now(timezone.utc)
                return WeatherData(
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=now,
                    valid_from=now - timedelta(minutes=30),
                    valid_until=now + timedelta(minutes=30),
                    temperature_c=current.get("temperature"),
                    precipitation_probability=None,
                    precipitation_mm=None,
                    condition=cond,
                    condition_text=text,
                    wind_speed_kmh=current.get("windspeed"),
                    is_severe=is_sev,
                    alerts=[],
                    provider=self.provider_name,
                    retrieved_at=now,
                    attribution=self.attribution,
                )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.error(f"Open-Meteo current weather failed: {exc}")
            raise RuntimeError(f"Open-Meteo service unreachable: {exc}") from exc

    def _parse_hourly_data(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        target_time: datetime,
    ) -> WeatherData:
        """
        Finds the hourly forecast bucket matching target_time.
        """
        now = datetime.now(timezone.utc)
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])

        if not times:
            # Fallback to current weather if hourly block is absent
            current = data.get("current_weather", {})
            cond, text, is_sev = self._map_wmo_code(current.get("weathercode"))
            return WeatherData(
                latitude=latitude,
                longitude=longitude,
                timestamp=now,
                valid_from=target_time - timedelta(minutes=30),
                valid_until=target_time + timedelta(minutes=30),
                temperature_c=current.get("temperature"),
                precipitation_probability=None,
                precipitation_mm=None,
                condition=cond,
                condition_text=text,
                wind_speed_kmh=current.get("windspeed"),
                is_severe=is_sev,
                alerts=[],
                provider=self.provider_name,
                retrieved_at=now,
                attribution=self.attribution,
            )

        # Target time in UTC
        target_utc = target_time.astimezone(timezone.utc) if target_time.tzinfo else target_time.replace(tzinfo=timezone.utc)

        # Match closest hour string 'YYYY-MM-DDTHH:00'
        target_hour_str = target_utc.strftime("%Y-%m-%dT%H:00")

        best_idx = 0
        min_diff = float("inf")
        for idx, t_str in enumerate(times):
            try:
                t_dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                diff = abs((t_dt - target_utc).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    best_idx = idx
            except Exception:
                continue

        wcode = hourly.get("weathercode", [None])[best_idx] if best_idx < len(hourly.get("weathercode", [])) else None
        cond, text, is_sev = self._map_wmo_code(wcode)

        temp = hourly.get("temperature_2m", [None])[best_idx] if best_idx < len(hourly.get("temperature_2m", [])) else None
        precip_prob = hourly.get("precipitation_probability", [None])[best_idx] if best_idx < len(hourly.get("precipitation_probability", [])) else None
        precip_mm = hourly.get("precipitation", [None])[best_idx] if best_idx < len(hourly.get("precipitation", [])) else None
        wind = hourly.get("windspeed_10m", [None])[best_idx] if best_idx < len(hourly.get("windspeed_10m", [])) else None

        # Build alerts if severe
        alerts: list[WeatherAlert] = []
        if is_sev:
            alerts.append(
                WeatherAlert(
                    title=f"Severe Weather Alert: {text}",
                    description=f"{text} expected in the area with potential impact on travel conditions.",
                    severity=WeatherAlertSeverity.SEVERE if "violent" in text.lower() or "hail" in text.lower() else WeatherAlertSeverity.MODERATE,
                    valid_from=target_utc - timedelta(hours=1),
                    valid_until=target_utc + timedelta(hours=1),
                    source="Open-Meteo",
                    official_url="https://open-meteo.com",
                )
            )

        # Valid window is +/- 30 minutes of that forecast hour
        forecast_dt = datetime.fromisoformat(times[best_idx]).replace(tzinfo=timezone.utc)
        valid_from = forecast_dt - timedelta(minutes=30)
        valid_until = forecast_dt + timedelta(minutes=30)

        return WeatherData(
            latitude=latitude,
            longitude=longitude,
            timestamp=forecast_dt,
            valid_from=valid_from,
            valid_until=valid_until,
            temperature_c=float(temp) if temp is not None else None,
            precipitation_probability=int(precip_prob) if precip_prob is not None else None,
            precipitation_mm=float(precip_mm) if precip_mm is not None else None,
            condition=cond,
            condition_text=text,
            wind_speed_kmh=float(wind) if wind is not None else None,
            is_severe=is_sev or bool(alerts),
            alerts=alerts,
            provider=self.provider_name,
            retrieved_at=now,
            attribution=self.attribution,
        )
