from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, List, Optional, Union

from pydantic import Field, computed_field, model_validator

from app.models.alarm import AlarmStatus, TransportMode
from app.schemas.base import BaseSchema
from app.schemas.destination import DestinationResponse
from app.schemas.schedule import AlarmScheduleSchema


class AlarmBase(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=150, description="Alarm display title")
    name: Optional[str] = Field(None, min_length=1, max_length=150, description="Alias for title")
    destination_id: Optional[uuid.UUID] = Field(None, description="Target destination UUID")
    arrival_time: Optional[time] = Field(None, description="Target arrival time (HH:MM:SS)")
    arrival_date: Optional[date] = Field(None, description="Specific calendar date for arrival")
    preparation_time: Optional[int] = Field(None, ge=0, le=360, description="Prep time in minutes")
    preparation_duration_seconds: Optional[int] = Field(None, ge=0, description="Prep duration in seconds")
    safety_buffer: Optional[int] = Field(None, ge=0, le=180, description="Safety traffic buffer in minutes")
    safety_buffer_seconds: Optional[int] = Field(None, ge=0, description="Safety buffer in seconds")
    transportation_mode: Optional[TransportMode] = Field(None, description="Mode of travel")
    travel_mode: Optional[TransportMode] = Field(None, description="Alias for transportation_mode")
    enabled: bool = Field(default=True, description="Whether alarm is actively armed")
    timezone: str = Field(default="Asia/Kolkata", description="IANA timezone identifier")
    origin_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional custom origin latitude")
    origin_lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional custom origin longitude")


class AlarmCreate(AlarmBase):
    schedule: Optional[AlarmScheduleSchema] = Field(
        default=None,
        description="Alarm recurrence configuration",
    )
    arrival_date_time: Optional[datetime] = Field(None, description="Full ISO arrival datetime")
    override_base_duration_seconds: Optional[int] = Field(None, ge=0, description="Client precalculated duration")

    @model_validator(mode="before")
    @classmethod
    def harmonize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # 1. Title / Name harmonization
        if not data.get("title") and data.get("name"):
            data["title"] = data["name"]
        elif not data.get("title") and not data.get("name"):
            data["title"] = "Smart Alarm"

        # 2. Destination ID harmonization
        if not data.get("destination_id") and data.get("destinationId"):
            data["destination_id"] = data["destinationId"]
        if not data.get("destination_id"):
            raise ValueError("destination_id is required")

        # 3. Arrival datetime / time harmonization
        dt_val = data.get("arrival_date_time") or data.get("arrivalDateTime")
        if dt_val:
            if isinstance(dt_val, str):
                dt_obj = datetime.fromisoformat(dt_val)
            else:
                dt_obj = dt_val
            data["arrival_time"] = dt_obj.time().replace(microsecond=0)
            data["arrival_date"] = dt_obj.date()
        elif data.get("arrival_time"):
            t_val = data["arrival_time"]
            if isinstance(t_val, str):
                parts = t_val.split(":")
                h = int(parts[0])
                m = int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                data["arrival_time"] = time(h, m, s)
        elif data.get("arrivalTime"):
            t_val = data["arrivalTime"]
            if isinstance(t_val, str):
                parts = t_val.split(":")
                h = int(parts[0])
                m = int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                data["arrival_time"] = time(h, m, s)
        else:
            raise ValueError("arrival_time or arrival_date_time is required")

        # 4. Preparation duration harmonization
        prep_sec = data.get("preparation_duration_seconds") or data.get("preparationDurationSeconds")
        if prep_sec is not None:
            data["preparation_time"] = prep_sec // 60
        elif data.get("preparation_time") is None:
            data["preparation_time"] = 30

        # 5. Safety buffer harmonization
        buf_sec = data.get("safety_buffer_seconds") or data.get("safetyBufferSeconds")
        if buf_sec is not None:
            data["safety_buffer"] = buf_sec // 60
        elif data.get("safety_buffer") is None:
            data["safety_buffer"] = 15

        # 6. Travel mode harmonization
        mode = data.get("transportation_mode") or data.get("travel_mode") or data.get("travelMode")
        if mode:
            if isinstance(mode, str):
                data["transportation_mode"] = TransportMode(mode.lower())
            else:
                data["transportation_mode"] = mode
        else:
            data["transportation_mode"] = TransportMode.DRIVING

        # 7. Recurrence / specific date schedule linkage
        arr_date = data.get("arrival_date") or data.get("arrivalDate")
        if arr_date and not data.get("schedule"):
            data["schedule"] = {
                "schedule_type": "once",
                "specific_date": arr_date,
            }

        return data


class AlarmUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    destination_id: Optional[uuid.UUID] = None
    arrival_time: Optional[time] = None
    arrival_date: Optional[date] = None
    arrival_date_time: Optional[datetime] = None
    preparation_time: Optional[int] = Field(None, ge=0, le=360)
    preparation_duration_seconds: Optional[int] = Field(None, ge=0)
    safety_buffer: Optional[int] = Field(None, ge=0, le=180)
    safety_buffer_seconds: Optional[int] = Field(None, ge=0)
    transportation_mode: Optional[TransportMode] = None
    travel_mode: Optional[TransportMode] = None
    enabled: Optional[bool] = None
    status: Optional[AlarmStatus] = None
    timezone: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    override_base_duration_seconds: Optional[int] = None
    schedule: Optional[AlarmScheduleSchema] = None

    @model_validator(mode="before")
    @classmethod
    def harmonize_update_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if not data.get("title") and data.get("name"):
            data["title"] = data["name"]

        if not data.get("destination_id") and data.get("destinationId"):
            data["destination_id"] = data["destinationId"]

        dt_val = data.get("arrival_date_time") or data.get("arrivalDateTime")
        if dt_val:
            if isinstance(dt_val, str):
                dt_obj = datetime.fromisoformat(dt_val)
            else:
                dt_obj = dt_val
            data["arrival_time"] = dt_obj.time().replace(microsecond=0)
            data["arrival_date"] = dt_obj.date()
        elif data.get("arrivalTime"):
            t_val = data["arrivalTime"]
            if isinstance(t_val, str):
                parts = t_val.split(":")
                h = int(parts[0])
                m = int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                data["arrival_time"] = time(h, m, s)

        prep_sec = data.get("preparation_duration_seconds") or data.get("preparationDurationSeconds")
        if prep_sec is not None:
            data["preparation_time"] = prep_sec // 60

        buf_sec = data.get("safety_buffer_seconds") or data.get("safetyBufferSeconds")
        if buf_sec is not None:
            data["safety_buffer"] = buf_sec // 60

        mode = data.get("transportation_mode") or data.get("travel_mode") or data.get("travelMode")
        if mode:
            if isinstance(mode, str):
                data["transportation_mode"] = TransportMode(mode.lower())
            else:
                data["transportation_mode"] = mode

        return data


class AlarmScheduleChangeResponse(BaseSchema):
    id: uuid.UUID
    alarm_id: uuid.UUID
    previous_wake_time: Optional[datetime] = None
    new_wake_time: datetime
    previous_leave_time: Optional[datetime] = None
    new_leave_time: datetime
    previous_planned_arrival: Optional[datetime] = None
    new_planned_arrival: datetime
    previous_travel_minutes: Optional[int] = None
    new_travel_minutes: int
    reason: str
    schedule_version: int
    created_at: datetime


class AlarmResponse(AlarmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    destination_id: uuid.UUID
    title: str
    arrival_time: time
    preparation_time: int
    safety_buffer: int
    transportation_mode: TransportMode
    enabled: bool
    status: AlarmStatus = AlarmStatus.SCHEDULED
    timezone: str = "Asia/Kolkata"
    calculation_version: str = "eta-v1"

    # Step 8: Dynamic Recalculation & History
    schedule_version: int = 1
    last_route_refresh_at: Optional[datetime] = None
    last_schedule_change_at: Optional[datetime] = None
    schedule_change_reason: Optional[str] = None
    route_freshness_state: str = "fresh"

    # Step 10: Weather + Calendar Context
    weather_buffer_minutes: Optional[int] = 0
    weather_condition_snapshot: Optional[str] = None
    calendar_event_id: Optional[uuid.UUID] = None

    # Associated entities
    destination: Optional[DestinationResponse] = None
    schedule: Optional[AlarmScheduleSchema] = None
    schedule_changes: Optional[List[AlarmScheduleChangeResponse]] = None

    # Dynamically calculated outputs
    calculated_wake_time: Optional[datetime] = None
    calculated_leave_time: Optional[datetime] = None
    planned_arrival_time: Optional[datetime] = None
    current_travel_minutes: Optional[int] = 0
    traffic_delay_minutes: Optional[int] = 0
    last_evaluated_at: Optional[datetime] = None
    last_calculated_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    name: Optional[str] = None
    wake_time: Optional[datetime] = None
    leave_time: Optional[datetime] = None
    travel_mode: Optional[str] = None
    preparation_duration_seconds: Optional[int] = None
    safety_buffer_seconds: Optional[int] = None
    arrival_date: Optional[date] = None

    @model_validator(mode="after")
    def populate_derived_fields(self) -> AlarmResponse:
        if not self.name:
            self.name = self.title
        if not self.wake_time:
            self.wake_time = self.calculated_wake_time
        if not self.leave_time:
            self.leave_time = self.calculated_leave_time
        if not self.travel_mode and self.transportation_mode:
            self.travel_mode = (
                self.transportation_mode.value
                if hasattr(self.transportation_mode, "value")
                else str(self.transportation_mode)
            )
        if self.preparation_duration_seconds is None:
            self.preparation_duration_seconds = self.preparation_time * 60
        if self.safety_buffer_seconds is None:
            self.safety_buffer_seconds = self.safety_buffer * 60
        if not self.arrival_date and self.schedule and self.schedule.specific_date:
            self.arrival_date = self.schedule.specific_date
        return self


class AlarmCalculateResult(BaseSchema):
    """Schema for calculation preview outputs."""

    recommended_wake_time: Union[str, datetime]
    recommended_leave_time: Union[str, datetime]
    planned_arrival_time: Optional[Union[str, datetime]] = None
    travel_minutes: int
    traffic_delay_minutes: int
    weather_summary: str = ""
    confidence_score: float = 1.0


AlarmResponse.model_rebuild()

