from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class WeatherCondition(str, enum.Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    FOG = "fog"
    WINDY = "windy"
    UNKNOWN = "unknown"


class WeatherAlertSeverity(str, enum.Enum):
    INFO = "info"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"


class WeatherAlert(BaseModel):
    title: str
    description: str
    severity: WeatherAlertSeverity = WeatherAlertSeverity.MODERATE
    valid_from: datetime
    valid_until: datetime
    source: str
    official_url: Optional[str] = None


class WeatherData(BaseModel):
    """
    Normalized, provider-independent weather representation for ADA.
    Does not expose vendor-specific payloads to domain or frontend layers.
    """
    latitude: float
    longitude: float
    timestamp: datetime
    valid_from: datetime
    valid_until: datetime
    temperature_c: Optional[float] = None
    precipitation_probability: Optional[int] = None  # Percentage 0-100
    precipitation_mm: Optional[float] = None
    condition: WeatherCondition = WeatherCondition.CLEAR
    condition_text: str = "Clear"
    wind_speed_kmh: Optional[float] = None
    is_severe: bool = False
    alerts: List[WeatherAlert] = Field(default_factory=list)
    provider: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attribution: str


class WeatherProvider(ABC):
    """
    Abstract interface for pluggable weather data providers.
    Supports Open-Meteo (default/free/no key needed), OpenWeatherMap, or mock providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the provider adapter."""
        pass

    @property
    @abstractmethod
    def attribution(self) -> str:
        """Provider attribution statement required by terms of service."""
        pass

    @abstractmethod
    async def get_forecast(
        self, latitude: float, longitude: float, target_time: datetime
    ) -> WeatherData:
        """
        Retrieves weather forecast for the specified location at or around target_time.
        """
        pass

    @abstractmethod
    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> WeatherData:
        """
        Retrieves the latest current observation for the specified coordinates.
        """
        pass
