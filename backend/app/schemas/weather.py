from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WeatherAlertSchema(BaseModel):
    title: str
    description: str
    severity: str
    valid_from: datetime
    valid_until: datetime
    source: str
    official_url: Optional[str] = None


class WeatherDataSchema(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime
    valid_from: datetime
    valid_until: datetime
    temperature_c: Optional[float] = None
    precipitation_probability: Optional[int] = None
    precipitation_mm: Optional[float] = None
    condition: str
    condition_text: str
    wind_speed_kmh: Optional[float] = None
    is_severe: bool = False
    alerts: List[WeatherAlertSchema] = Field(default_factory=list)
    provider: str
    retrieved_at: datetime
    attribution: str


class JourneyWeatherSummarySchema(BaseModel):
    has_precipitation: bool
    is_severe: bool
    condition: str
    condition_text: str
    precipitation_mm: Optional[float] = None
    temperature_c: Optional[float] = None
    is_stale: bool
    alerts: List[WeatherAlertSchema] = Field(default_factory=list)
    explanation: str
    provider: str
    attribution: str
