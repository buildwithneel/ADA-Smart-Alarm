from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    alarm_id: Optional[uuid.UUID] = None
    type: NotificationType
    status: NotificationStatus
    channel: NotificationChannel
    title: str
    body: str
    scheduled_for: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    schedule_version: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wake_alarm_enabled: bool = True
    departure_reminder_enabled: bool = True
    departure_reminder_lead_minutes: int = 10
    schedule_change_enabled: bool = True
    traffic_change_enabled: bool = True
    sound_enabled: bool = True
    vibration_enabled: bool = True
    in_app_enabled: bool = True
    web_push_enabled: bool = True


class NotificationPreferencesUpdate(BaseModel):
    wake_alarm_enabled: Optional[bool] = None
    departure_reminder_enabled: Optional[bool] = None
    departure_reminder_lead_minutes: Optional[int] = Field(None, ge=1, le=120)
    schedule_change_enabled: Optional[bool] = None
    traffic_change_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    vibration_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    web_push_enabled: Optional[bool] = None


class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(..., min_length=10)
    p256dh: str = Field(..., min_length=10)
    auth: str = Field(..., min_length=5)
    user_agent: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint: str
    is_active: bool
    created_at: datetime


class VapidKeyResponse(BaseModel):
    public_key: str


class NotificationTestRequest(BaseModel):
    type: Optional[NotificationType] = NotificationType.SYSTEM
    title: Optional[str] = "ADA Alarm Test"
    body: Optional[str] = "This is a test notification confirming delivery."
