import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query, status

from app.api.deps import (
    get_alarm_recalculation_service,
    get_alarm_repository,
    get_alarm_service,
    get_current_user,
)
from app.core.errors import NotFoundException
from app.models.alarm import AlarmStatus
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.schemas.alarm import (
    AlarmCreate,
    AlarmResponse,
    AlarmScheduleChangeResponse,
    AlarmUpdate,
)
from app.services.alarm_recalculation_service import AlarmRecalculationService
from app.services.alarm_service import AlarmService

router = APIRouter()


@router.get(
    "",
    response_model=List[AlarmResponse],
    summary="List Alarms",
    tags=["Alarms"],
)
def list_alarms(
    status: Optional[AlarmStatus] = Query(None, description="Filter by alarm status"),
    filter: Optional[str] = Query(None, description="Filter by category (upcoming, enabled, disabled, expired)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> List[AlarmResponse]:
    """
    Retrieve all smart alarms configured by the authenticated user.
    Results are sorted chronologically.
    """
    return alarm_service.list_alarms(
        user_id=current_user.id,
        status=status,
        filter_type=filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=AlarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Smart Alarm",
    tags=["Alarms"],
)
async def create_alarm(
    alarm_in: AlarmCreate,
    idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """
    Create a new arrival-based smart alarm.
    Calculates wake time, leave time, and planned arrival based on current ETA.
    Protected against duplicate submissions via X-Idempotency-Key.
    """
    return await alarm_service.create_alarm(
        user_id=current_user.id,
        data=alarm_in,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/{alarm_id}",
    response_model=AlarmResponse,
    summary="Get Alarm Details",
    tags=["Alarms"],
)
def get_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """Retrieve details and calculated schedule for a specific smart alarm by UUID."""
    return alarm_service.get_alarm(current_user.id, alarm_id)


@router.patch(
    "/{alarm_id}",
    response_model=AlarmResponse,
    summary="Update Alarm",
    tags=["Alarms"],
)
async def update_alarm(
    alarm_id: uuid.UUID,
    alarm_in: AlarmUpdate,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """
    Update arrival time, parameters, or recurring schedule for an alarm.
    Recalculates wake, leave, and planned arrival times if schedule parameters change.
    """
    return await alarm_service.update_alarm(current_user.id, alarm_id, alarm_in)


@router.delete(
    "/{alarm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Alarm",
    tags=["Alarms"],
)
def delete_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> None:
    """Delete an alarm and its associated recurrence schedule safely."""
    alarm_service.delete_alarm(current_user.id, alarm_id)


@router.post(
    "/{alarm_id}/enable",
    response_model=AlarmResponse,
    summary="Enable Alarm",
    tags=["Alarms"],
)
async def enable_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """Enables an alarm, transitioning its state to SCHEDULED and refreshing calculation."""
    return await alarm_service.enable_alarm(current_user.id, alarm_id)


@router.post(
    "/{alarm_id}/disable",
    response_model=AlarmResponse,
    summary="Disable Alarm",
    tags=["Alarms"],
)
def disable_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """Disables an alarm, preventing future active wake trigger monitoring."""
    return alarm_service.disable_alarm(current_user.id, alarm_id)


@router.post(
    "/{alarm_id}/duplicate",
    response_model=AlarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate Alarm",
    tags=["Alarms"],
)
async def duplicate_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_service: AlarmService = Depends(get_alarm_service),
) -> AlarmResponse:
    """Duplicates an alarm into a new independent record with its own UUID."""
    return await alarm_service.duplicate_alarm(current_user.id, alarm_id)


@router.post(
    "/{alarm_id}/refresh",
    response_model=AlarmResponse,
    summary="Refresh Alarm Route & Dynamic Recalculation",
    tags=["Alarms"],
)
async def refresh_alarm(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    recalc_service: AlarmRecalculationService = Depends(get_alarm_recalculation_service),
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
) -> AlarmResponse:
    """
    Manually refreshes routing and recalculates wake time, leave time, and planned arrival.
    Uses the unified AlarmRecalculationService for both manual and automatic calculations.
    """
    result = await recalc_service.recalculate_alarm(
        alarm_id=alarm_id,
        user_id=current_user.id,
        force=True,
    )
    if result.status == "not_found":
        raise NotFoundException("Alarm", alarm_id)

    alarm = alarm_repo.get_by_user_and_id(current_user.id, alarm_id)
    if not alarm:
        raise NotFoundException("Alarm", alarm_id)
    return AlarmResponse.model_validate(alarm)


@router.get(
    "/{alarm_id}/history",
    response_model=List[AlarmScheduleChangeResponse],
    summary="Get Alarm Schedule Recalculation History",
    tags=["Alarms"],
)
def get_alarm_history(
    alarm_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Max history records to return"),
    current_user: User = Depends(get_current_user),
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
) -> List[AlarmScheduleChangeResponse]:
    """
    Retrieves lightweight audit history of meaningful schedule changes for this alarm.
    Enforces user authorization.
    """
    alarm = alarm_repo.get_by_user_and_id(current_user.id, alarm_id)
    if not alarm:
        raise NotFoundException("Alarm", alarm_id)

    changes = alarm_repo.get_schedule_changes(alarm_id=alarm_id, limit=limit)
    return [AlarmScheduleChangeResponse.model_validate(c) for c in changes]

