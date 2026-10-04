from __future__ import annotations

import logging
from typing import Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.deps import (
    get_alarm_draft_service,
    get_assistant_conversation_service,
    get_current_user,
    get_intent_parser,
    get_personalization_service,
)
from app.core.config import settings
from app.core.errors import ConflictException, NotFoundException, ValidationException
from app.core.redis import get_redis_client
from app.models.assistant import DraftStatus
from app.models.user import User
from app.schemas.alarm import AlarmResponse
from app.schemas.assistant import (
    AlarmDraftConfirmRequest,
    AlarmDraftResponse,
    AlarmDraftUpdateRequest,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConversationResponse,
    AssistantMessageResponse,
    AssistantStatusResponse,
    DeleteConversationsResponse,
    IntentType,
    ParsedIntent,
)
from app.services.alarm_draft_service import AlarmDraftService
from app.services.assistant_conversation_service import AssistantConversationService
from app.services.intent_parser import IntentParser
from app.services.personalization_service import PersonalizationService

logger = logging.getLogger("ada.api.assistant")

router = APIRouter()

# In-memory fallback for rate limiting if Redis is unavailable
_in_memory_rate_limits: Dict[str, List[float]] = {}


def _enforce_rate_limit(user_id: uuid.UUID) -> None:
    """Enforces per-user rate limit on AI assistant interactions."""
    limit = getattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 20)
    key = f"ada:ratelimit:ai:{user_id}"

    try:
        redis_client = get_redis_client()
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 60)
        if current > limit:
            logger.warning(f"Rate limit exceeded for user {user_id} on assistant endpoint.")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            )
    except HTTPException:
        raise
    except Exception:
        # Fall back to in-memory window tracking
        import time

        now = time.time()
        timestamps = _in_memory_rate_limits.setdefault(str(user_id), [])
        # Evict timestamps older than 60s
        _in_memory_rate_limits[str(user_id)] = [t for t in timestamps if now - t < 60]
        if len(_in_memory_rate_limits[str(user_id)]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            )
        _in_memory_rate_limits[str(user_id)].append(now)


# ----------------------------------------------------------------------
# Assistant Chat & Interaction
# ----------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Submit Natural Language Assistant Message",
)
async def assistant_chat(
    req: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    intent_parser: IntentParser = Depends(get_intent_parser),
    draft_service: AlarmDraftService = Depends(get_alarm_draft_service),
    conversation_service: AssistantConversationService = Depends(get_assistant_conversation_service),
    personalization_service: PersonalizationService = Depends(get_personalization_service),
) -> AssistantChatResponse:
    """
    Main conversational endpoint:
    1. Enforces rate limiting per authenticated user.
    2. Parses natural language intent without inventing data.
    3. Handles clarification when info is missing or ambiguous.
    4. Computes deterministic schedule & draft preview when data is sufficient.
    5. NEVER creates alarms directly without explicit user confirmation.
    """
    _enforce_rate_limit(current_user.id)

    # 1. Resolve conversation session
    conv = conversation_service.get_or_create_conversation(
        user_id=current_user.id,
        conversation_id=req.conversation_id,
        title=f"Chat {req.message[:30]}..." if not req.conversation_id else "Assistant Chat",
    )

    # 2. Record user message turn
    conversation_service.add_message(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="user",
        content=req.message,
    )

    # 3. Parse user intent
    parsed_intent = await intent_parser.parse(
        prompt=req.message,
        user_id=current_user.id,
        client_timezone=req.client_timezone or current_user.timezone or "Asia/Kolkata",
        origin_lat=req.origin_lat,
        origin_lng=req.origin_lng,
    )

    clarification_questions: List[str] = []
    draft_resp: Optional[AlarmDraftResponse] = None

    # 4. Handle General Query / Neutralized Prompt Injections / Explanations without draft creation
    if parsed_intent.intent_type in {IntentType.GENERAL_QUERY, IntentType.EXPLAIN_SCHEDULE}:
        reply_content = parsed_intent.explanation or (
            "I am ADA's AI Assistant. You can describe when and where you need to arrive, "
            "and I will prepare an editable Smart Alarm draft with real ETA calculations."
        )
        asst_msg = conversation_service.add_message(
            conversation_id=conv.id,
            user_id=current_user.id,
            role="assistant",
            content=reply_content,
        )
        return AssistantChatResponse(
            conversation_id=conv.id,
            message=AssistantMessageResponse.model_validate(asst_msg),
            parsed_intent=parsed_intent,
            draft=None,
            requires_clarification=False,
            missing_fields=[],
            clarification_questions=[],
            provider=intent_parser.ai_provider.provider_name,
        )

    # 5. Check for clarification conditions
    if parsed_intent.missing_fields or parsed_intent.ambiguities:
        for field in parsed_intent.missing_fields:
            if field == "destination":
                clarification_questions.append("Where are you heading? (e.g. 'CHARUSAT University', 'College', 'Office')")
            elif field == "arrival_time":
                clarification_questions.append("What time do you need to arrive? (e.g. '9:00 AM' or '14:00')")
            elif field == "arrival_time_clarification":
                clarification_questions.append("Did you mean morning (AM) or afternoon/evening (PM)?")
            elif field == "future_arrival_time":
                clarification_questions.append("The requested arrival time is in the past. What future date/time should we schedule for?")
            else:
                clarification_questions.append(f"Please provide {field.replace('_', ' ')}.")

        reply_content = (
            "I'd love to set up this smart alarm for you, but I need a little more information:\n• "
            + "\n• ".join(clarification_questions)
        )

        asst_msg = conversation_service.add_message(
            conversation_id=conv.id,
            user_id=current_user.id,
            role="assistant",
            content=reply_content,
            metadata={"missing_fields": parsed_intent.missing_fields, "ambiguities": parsed_intent.ambiguities},
        )

        return AssistantChatResponse(
            conversation_id=conv.id,
            message=AssistantMessageResponse.model_validate(asst_msg),
            parsed_intent=parsed_intent,
            draft=None,
            requires_clarification=True,
            missing_fields=parsed_intent.missing_fields,
            clarification_questions=clarification_questions,
            provider=intent_parser.ai_provider.provider_name,
        )

    # 5. Intent is complete: generate or update draft deterministically
    if req.draft_id:
        # Update existing draft
        update_data = AlarmDraftUpdateRequest(
            title=parsed_intent.title,
            destination_text=parsed_intent.destination_text,
            arrival_time=parsed_intent.required_arrival_time,
            arrival_date=parsed_intent.arrival_date,
            preparation_time=parsed_intent.preparation_duration_minutes,
            safety_buffer=parsed_intent.safety_buffer_minutes,
            transportation_mode=parsed_intent.transport_mode,
            timezone=parsed_intent.timezone,
        )
        draft = await draft_service.update_draft(
            user_id=current_user.id,
            draft_id=req.draft_id,
            data=update_data,
            origin_lat=req.origin_lat,
            origin_lng=req.origin_lng,
        )
    else:
        # Create fresh draft
        draft = await draft_service.create_draft_from_intent(
            user_id=current_user.id,
            intent=parsed_intent,
            conversation_id=conv.id,
            origin_lat=req.origin_lat,
            origin_lng=req.origin_lng,
        )

    draft_resp = AlarmDraftResponse.model_validate(draft)

    reply_content = draft.explanation or (
        f"I've prepared a draft schedule for {draft.destination_text} with arrival at "
        f"{draft.arrival_time.strftime('%I:%M %p')}. Please review the details and confirm below."
    )

    asst_msg = conversation_service.add_message(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="assistant",
        content=reply_content,
        metadata={"draft_id": str(draft.id)},
    )

    return AssistantChatResponse(
        conversation_id=conv.id,
        message=AssistantMessageResponse.model_validate(asst_msg),
        parsed_intent=parsed_intent,
        draft=draft_resp,
        requires_clarification=False,
        missing_fields=[],
        clarification_questions=[],
        provider=intent_parser.ai_provider.provider_name,
    )


# ----------------------------------------------------------------------
# Alarm Drafts CRUD & Confirmation
# ----------------------------------------------------------------------

@router.get(
    "/drafts/{draft_id}",
    response_model=AlarmDraftResponse,
    summary="Get Alarm Draft",
)
def get_alarm_draft(
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    draft_service: AlarmDraftService = Depends(get_alarm_draft_service),
) -> AlarmDraftResponse:
    """Retrieves an existing Alarm Draft for user inspection."""
    draft = draft_service.get_draft(current_user.id, draft_id)
    return AlarmDraftResponse.model_validate(draft)


@router.patch(
    "/drafts/{draft_id}",
    response_model=AlarmDraftResponse,
    summary="Update Alarm Draft",
)
async def update_alarm_draft(
    draft_id: uuid.UUID,
    data: AlarmDraftUpdateRequest,
    current_user: User = Depends(get_current_user),
    draft_service: AlarmDraftService = Depends(get_alarm_draft_service),
) -> AlarmDraftResponse:
    """Allows user to edit every extracted field before submitting the alarm."""
    draft = await draft_service.update_draft(
        user_id=current_user.id,
        draft_id=draft_id,
        data=data,
    )
    return AlarmDraftResponse.model_validate(draft)


@router.post(
    "/drafts/{draft_id}/confirm",
    response_model=AlarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm Alarm Draft and Schedule Alarm",
)
async def confirm_alarm_draft(
    draft_id: uuid.UUID,
    confirm_in: Optional[AlarmDraftConfirmRequest] = None,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    draft_service: AlarmDraftService = Depends(get_alarm_draft_service),
) -> AlarmResponse:
    """
    Explicit user confirmation action.
    Creates and schedules the real alarm using ADA's deterministic AlarmService.
    Idempotency protected to prevent duplicate alarm creation on double clicks.
    """
    key = confirm_in.idempotency_key if confirm_in and confirm_in.idempotency_key else x_idempotency_key
    return await draft_service.confirm_draft(
        user_id=current_user.id,
        draft_id=draft_id,
        idempotency_key=key,
    )


@router.post(
    "/drafts/{draft_id}/discard",
    response_model=AlarmDraftResponse,
    summary="Discard Alarm Draft",
)
def discard_alarm_draft(
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    draft_service: AlarmDraftService = Depends(get_alarm_draft_service),
) -> AlarmDraftResponse:
    """Discards an active alarm draft."""
    draft = draft_service.discard_draft(current_user.id, draft_id)
    return AlarmDraftResponse.model_validate(draft)


# ----------------------------------------------------------------------
# Conversations & History
# ----------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=List[AssistantConversationResponse],
    summary="List Assistant Conversations",
)
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    conv_service: AssistantConversationService = Depends(get_assistant_conversation_service),
) -> List[AssistantConversationResponse]:
    return conv_service.list_conversations(current_user.id, skip=skip, limit=limit)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationResponse,
    summary="Get Conversation Detail",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conv_service: AssistantConversationService = Depends(get_assistant_conversation_service),
) -> AssistantConversationResponse:
    return conv_service.get_conversation(current_user.id, conversation_id)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Specific Conversation",
)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conv_service: AssistantConversationService = Depends(get_assistant_conversation_service),
) -> None:
    conv_service.delete_conversation(current_user.id, conversation_id)


@router.delete(
    "/conversations",
    response_model=DeleteConversationsResponse,
    summary="Delete All Conversation History",
)
def delete_all_conversations(
    current_user: User = Depends(get_current_user),
    conv_service: AssistantConversationService = Depends(get_assistant_conversation_service),
) -> DeleteConversationsResponse:
    count = conv_service.delete_all_conversations(current_user.id)
    return DeleteConversationsResponse(message="All conversations deleted.", count=count)


# ----------------------------------------------------------------------
# Assistant Status & Availability
# ----------------------------------------------------------------------

@router.get(
    "/status",
    response_model=AssistantStatusResponse,
    summary="Get AI Provider Availability",
)
async def get_assistant_status(
    intent_parser: IntentParser = Depends(get_intent_parser),
) -> AssistantStatusResponse:
    is_healthy = await intent_parser.ai_provider.health_check()
    return AssistantStatusResponse(
        status="online" if is_healthy else "degraded",
        provider=intent_parser.ai_provider.provider_name,
        model=getattr(settings, "AI_MODEL_NAME", "gemini-1.5-flash"),
        fallback_available=True,
    )
