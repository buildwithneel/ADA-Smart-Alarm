from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.models.alarm import TransportMode
from app.models.assistant import DraftStatus
from app.schemas.base import BaseSchema


class IntentType(str, enum.Enum):
    CREATE_ALARM = "create_alarm"
    UPDATE_DRAFT = "update_draft"
    EXPLAIN_SCHEDULE = "explain_schedule"
    ASK_CLARIFICATION = "ask_clarification"
    GENERAL_QUERY = "general_query"


class ParsedIntent(BaseSchema):
    """Normalized structured intent extracted from natural language input."""

    intent_type: IntentType = Field(default=IntentType.CREATE_ALARM)
    title: Optional[str] = Field(None, max_length=150)
    destination_text: Optional[str] = Field(None, max_length=500)
    destination_place_id: Optional[str] = Field(None, max_length=255)
    required_arrival_time: Optional[time] = None
    arrival_date: Optional[date] = None
    timezone: Optional[str] = Field(default="Asia/Kolkata", max_length=50)
    preparation_duration_minutes: Optional[int] = Field(None, ge=0, le=360)
    safety_buffer_minutes: Optional[int] = Field(None, ge=0, le=180)
    transport_mode: Optional[TransportMode] = None
    missing_fields: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: Optional[str] = None


class AssistantChatRequest(BaseSchema):
    """User prompt sent to the Assistant API."""

    message: str = Field(..., min_length=1, max_length=1000, description="Natural language prompt")
    conversation_id: Optional[uuid.UUID] = None
    draft_id: Optional[uuid.UUID] = None
    client_timezone: Optional[str] = Field(default="Asia/Kolkata", max_length=50)
    origin_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    origin_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned


class AlarmDraftResponse(BaseSchema):
    """Full detail of an editable Alarm Draft."""

    id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    title: str
    destination_text: str
    destination_id: Optional[uuid.UUID] = None
    destination_address: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    arrival_time: time
    arrival_date: Optional[date] = None
    preparation_time: int
    safety_buffer: int
    transportation_mode: TransportMode
    timezone: str
    calculated_wake_time: Optional[datetime] = None
    calculated_leave_time: Optional[datetime] = None
    planned_arrival_time: Optional[datetime] = None
    travel_duration_minutes: int
    traffic_delay_minutes: int
    status: DraftStatus
    explanation: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AlarmDraftUpdateRequest(BaseSchema):
    """Payload to modify any field of an active draft."""

    title: Optional[str] = Field(None, max_length=150)
    destination_text: Optional[str] = Field(None, max_length=500)
    arrival_time: Optional[time] = None
    arrival_date: Optional[date] = None
    preparation_time: Optional[int] = Field(None, ge=0, le=360)
    safety_buffer: Optional[int] = Field(None, ge=0, le=180)
    transportation_mode: Optional[TransportMode] = None
    timezone: Optional[str] = Field(None, max_length=50)


class AlarmDraftConfirmRequest(BaseSchema):
    """Payload to confirm draft creation."""

    idempotency_key: Optional[str] = Field(None, max_length=100)


class AssistantMessageResponse(BaseSchema):
    """Single message response representation."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    metadata_json: Optional[str] = None
    created_at: datetime


class AssistantConversationResponse(BaseSchema):
    """Full conversation with messages."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    messages: List[AssistantMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AssistantChatResponse(BaseSchema):
    """Composite response returned by POST /api/v1/assistant/chat."""

    conversation_id: uuid.UUID
    message: AssistantMessageResponse
    parsed_intent: ParsedIntent
    draft: Optional[AlarmDraftResponse] = None
    requires_clarification: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    provider: str = Field(default="mock")


class PersonalizationResponse(BaseSchema):
    """Transparent view of user personalization settings."""

    user_id: uuid.UUID
    default_transportation: TransportMode
    default_preparation_time: int
    default_safety_buffer: int
    assistant_response_style: str
    save_conversation_history: bool
    use_alarm_history_suggestions: bool
    weather_buffer_enabled: bool
    calendar_sync_enabled: bool


class PersonalizationUpdate(BaseSchema):
    """Payload to modify personalization settings."""

    default_transportation: Optional[TransportMode] = None
    default_preparation_time: Optional[int] = Field(None, ge=0, le=360)
    default_safety_buffer: Optional[int] = Field(None, ge=0, le=180)
    assistant_response_style: Optional[str] = Field(None, max_length=50)
    save_conversation_history: Optional[bool] = None
    use_alarm_history_suggestions: Optional[bool] = None
    weather_buffer_enabled: Optional[bool] = None
    calendar_sync_enabled: Optional[bool] = None


class AssistantStatusResponse(BaseSchema):
    """Health and status of AI provider."""

    status: str
    provider: str
    model: str
    fallback_available: bool


class DeleteConversationsResponse(BaseSchema):
    """Response returned upon purging conversations."""

    message: str
    count: int
