from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CalendarConnectionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    account_email: str
    is_active: bool
    last_synced_at: Optional[datetime] = None
    sync_status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarEventResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    user_id: uuid.UUID
    alarm_id: Optional[uuid.UUID] = None
    external_event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    timezone: str
    location: Optional[str] = None
    resolved_latitude: Optional[float] = None
    resolved_longitude: Optional[float] = None
    all_day: bool
    status: str
    source_provider: str
    last_synced_at: datetime
    event_link: Optional[str] = None

    class Config:
        from_attributes = True


class CalendarOAuthUrlResponse(BaseModel):
    authorization_url: str
    provider: str


class CalendarOAuthCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: Optional[str] = None


class ProposeAlarmFromEventResponse(BaseModel):
    already_linked: bool = False
    alarm_id: Optional[str] = None
    alarm_title: Optional[str] = None
    event_id: Optional[str] = None
    event_title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    has_usable_location: bool = False
    resolved_latitude: Optional[float] = None
    resolved_longitude: Optional[float] = None
    proposed_arrival_time: Optional[str] = None
    proposed_arrival_date: Optional[str] = None
    preparation_time: int = 30
    safety_buffer: int = 15
    transportation_mode: str = "driving"


class CreateAlarmFromEventRequest(BaseModel):
    title: Optional[str] = None
    destination_id: Optional[uuid.UUID] = None
    preparation_time: Optional[int] = Field(default=None, ge=0, le=180)
    safety_buffer: Optional[int] = Field(default=None, ge=0, le=120)
    transportation_mode: Optional[str] = "driving"
