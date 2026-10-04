import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.alarm import TransportMode
from app.models.preference import DistanceUnit, ThemeMode, TimeFormat
from app.schemas.base import BaseSchema


class UserPreferenceBase(BaseSchema):
    default_transportation: TransportMode = Field(default=TransportMode.DRIVING)
    default_preparation_time: int = Field(
        default=30, ge=0, le=360, description="Preparation time in minutes"
    )
    default_safety_buffer: int = Field(
        default=15, ge=0, le=180, description="Safety buffer in minutes"
    )
    distance_units: DistanceUnit = Field(default=DistanceUnit.KM)
    time_format: TimeFormat = Field(default=TimeFormat.H12)
    theme: ThemeMode = Field(default=ThemeMode.DARK)
    sound_enabled: bool = Field(default=True)
    vibration_enabled: bool = Field(default=True)
    pre_alarm_notification: bool = Field(default=True)
    wake_alarm_enabled: bool = Field(default=True)
    departure_reminder_enabled: bool = Field(default=True)
    departure_reminder_lead_minutes: int = Field(default=10, ge=1, le=120)
    schedule_change_enabled: bool = Field(default=True)
    traffic_change_enabled: bool = Field(default=True)
    in_app_enabled: bool = Field(default=True)
    web_push_enabled: bool = Field(default=True)
    # Step 10: Weather + Calendar Context Preferences
    weather_buffer_enabled: bool = Field(default=False)
    weather_buffer_mode: str = Field(default="informational_only")
    weather_buffer_minutes: int = Field(default=10, ge=0, le=30)
    weather_alerts_enabled: bool = Field(default=True)
    calendar_sync_enabled: bool = Field(default=True)
    calendar_auto_reschedule: bool = Field(default=False)
    # Step 11: Personalization Preferences
    assistant_response_style: str = Field(default="concise")
    save_conversation_history: bool = Field(default=True)
    use_alarm_history_suggestions: bool = Field(default=True)


class UserPreferenceUpdate(BaseSchema):
    default_transportation: Optional[TransportMode] = None
    default_preparation_time: Optional[int] = Field(None, ge=0, le=360)
    default_safety_buffer: Optional[int] = Field(None, ge=0, le=180)
    distance_units: Optional[DistanceUnit] = None
    time_format: Optional[TimeFormat] = None
    theme: Optional[ThemeMode] = None
    sound_enabled: Optional[bool] = None
    vibration_enabled: Optional[bool] = None
    pre_alarm_notification: Optional[bool] = None
    wake_alarm_enabled: Optional[bool] = None
    departure_reminder_enabled: Optional[bool] = None
    departure_reminder_lead_minutes: Optional[int] = Field(None, ge=1, le=120)
    schedule_change_enabled: Optional[bool] = None
    traffic_change_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    web_push_enabled: Optional[bool] = None
    # Step 10: Context Preferences Update
    weather_buffer_enabled: Optional[bool] = None
    weather_buffer_mode: Optional[str] = None
    weather_buffer_minutes: Optional[int] = Field(None, ge=0, le=30)
    weather_alerts_enabled: Optional[bool] = None
    calendar_sync_enabled: Optional[bool] = None
    calendar_auto_reschedule: Optional[bool] = None
    # Step 11: Personalization Update
    assistant_response_style: Optional[str] = None
    save_conversation_history: Optional[bool] = None
    use_alarm_history_suggestions: Optional[bool] = None


class UserPreferenceResponse(UserPreferenceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
