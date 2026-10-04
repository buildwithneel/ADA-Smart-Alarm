from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContextResultResponse(BaseModel):
    context_type: str
    source: str
    evaluated_at: datetime
    valid_time_window: Dict[str, Optional[str]]
    freshness: str
    relevance: str
    finding: str
    recommended_action: str
    recommended_buffer_minutes: int
    requires_confirmation: bool
    explanation: str
    policy_version: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextSummaryResponse(BaseModel):
    alarm_id: uuid.UUID
    evaluated_at: datetime
    results: List[ContextResultResponse]
    has_weather_warning: bool = False
    has_calendar_warning: bool = False
    recommended_total_buffer: int = 0


class ApplyWeatherBufferRequest(BaseModel):
    buffer_minutes: Optional[int] = Field(default=None, ge=0, le=30)
    expected_version: Optional[int] = None


class ContextPreferencesResponse(BaseModel):
    weather_buffer_enabled: bool
    weather_buffer_mode: str  # disabled, informational_only, user_confirmed, automatic
    weather_buffer_minutes: int
    weather_alerts_enabled: bool
    calendar_sync_enabled: bool
    calendar_auto_reschedule: bool

    class Config:
        from_attributes = True


class ContextPreferencesUpdate(BaseModel):
    weather_buffer_enabled: Optional[bool] = None
    weather_buffer_mode: Optional[str] = None  # disabled, informational_only, user_confirmed, automatic
    weather_buffer_minutes: Optional[int] = Field(default=None, ge=0, le=30)
    weather_alerts_enabled: Optional[bool] = None
    calendar_sync_enabled: Optional[bool] = None
    calendar_auto_reschedule: Optional[bool] = None
