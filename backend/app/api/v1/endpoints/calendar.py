from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.alarm import AlarmResponse
from app.schemas.calendar import (
    CalendarConnectionResponse,
    CalendarEventResponse,
    CalendarOAuthCallbackRequest,
    CalendarOAuthUrlResponse,
    CreateAlarmFromEventRequest,
    ProposeAlarmFromEventResponse,
)
from app.services.calendar.calendar_service import CalendarService

router = APIRouter()


@router.get(
    "/connections",
    response_model=List[CalendarConnectionResponse],
    summary="List active calendar connections for current user",
)
def list_calendar_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CalendarConnectionResponse]:
    user_id = current_user.id
    repo = CalendarRepository(db)
    conns = repo.list_user_connections(user_id)
    return [CalendarConnectionResponse.model_validate(c) for c in conns]


@router.post(
    "/connections/auth-url",
    response_model=CalendarOAuthUrlResponse,
    summary="Get OAuth authorization URL for calendar connection",
)
def get_calendar_auth_url(
    redirect_uri: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarOAuthUrlResponse:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    url = svc.get_authorization_url(user_id=user_id, redirect_uri=redirect_uri)
    return CalendarOAuthUrlResponse(authorization_url=url, provider="google")


@router.post(
    "/connections/callback",
    response_model=CalendarConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Handle OAuth redirect callback and store encrypted tokens",
)
async def handle_calendar_oauth_callback(
    payload: CalendarOAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarConnectionResponse:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    conn = await svc.handle_oauth_callback(
        user_id=user_id,
        code=payload.code,
        state=payload.state,
        redirect_uri=payload.redirect_uri,
    )
    return CalendarConnectionResponse.model_validate(conn)


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect and revoke calendar connection",
)
async def disconnect_calendar(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    await svc.disconnect_calendar(connection_id=connection_id, user_id=user_id)


@router.post(
    "/connections/{connection_id}/sync",
    summary="Trigger immediate synchronization of calendar events",
)
async def sync_calendar(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    # Check connection ownership
    conn = svc.calendar_repo.get_connection(connection_id)
    if not conn or conn.user_id != user_id:
        from app.core.errors import NotFoundException
        raise NotFoundException("Calendar connection not found.")

    return await svc.sync_connection_events(connection_id)


@router.get(
    "/events",
    response_model=List[CalendarEventResponse],
    summary="List upcoming calendar events for current user",
)
def list_calendar_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CalendarEventResponse]:
    user_id = current_user.id
    repo = CalendarRepository(db)
    events = repo.list_upcoming_events(user_id=user_id)
    return [CalendarEventResponse.model_validate(e) for e in events]


@router.get(
    "/events/{event_id}/propose-alarm",
    response_model=ProposeAlarmFromEventResponse,
    summary="Inspect event and get proposed alarm parameters for user review",
)
async def propose_alarm_from_calendar_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposeAlarmFromEventResponse:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    proposal = await svc.propose_alarm_from_event(event_id=event_id, user_id=user_id)
    return ProposeAlarmFromEventResponse.model_validate(proposal)


@router.post(
    "/events/{event_id}/create-alarm",
    response_model=AlarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm and create smart alarm based on calendar event",
)
async def create_alarm_from_calendar_event(
    event_id: uuid.UUID,
    payload: CreateAlarmFromEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlarmResponse:
    user_id = current_user.id
    svc = CalendarService(
        calendar_repo=CalendarRepository(db),
        alarm_repo=AlarmRepository(db),
        destination_repo=DestinationRepository(db),
        pref_repo=PreferenceRepository(db),
    )
    alarm = await svc.create_alarm_from_event(
        event_id=event_id,
        user_id=user_id,
        destination_id=payload.destination_id,
        title=payload.title,
        preparation_time=payload.preparation_time,
        safety_buffer=payload.safety_buffer,
        transportation_mode=payload.transportation_mode,
    )
    return AlarmResponse.model_validate(alarm)
