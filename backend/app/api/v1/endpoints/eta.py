"""
ETA Calculation Engine API Endpoints.

Provides the following routes:
  POST /eta/calculate   — Full ETA calculation with live routing + full breakdown
  POST /eta/preview     — Lightweight preview for live form updates (no auth required)
  POST /eta/alarms/{alarm_id}/evaluate  — Re-evaluate + persist ETA for a specific alarm
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_alarm_repository,
    get_current_user,
    get_eta_calculation_service,
    get_routing_service,
)
from app.core.errors import ForbiddenException, NotFoundException
from app.core.rate_limit import rate_limit_dependency
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.schemas.eta import (
    AlarmETAUpdateResult,
    ETACalculateRequest,
    ETACalculateResponse,
    ETAPreviewRequest,
    ETAPreviewResponse,
)
from app.services.eta_calculation_service import ETACalculationService
from app.services.routing_service import RoutingService

router = APIRouter()


@router.post(
    "/calculate",
    response_model=ETACalculateResponse,
    summary="Full ETA Calculation",
    tags=["ETA Engine"],
    dependencies=[Depends(rate_limit_dependency(prefix="eta_calc"))],
)
async def calculate_eta(
    payload: ETACalculateRequest,
    eta_service: ETACalculationService = Depends(get_eta_calculation_service),
    current_user: User = Depends(get_current_user),
) -> ETACalculateResponse:
    """
    Performs a full ETA calculation using ADA's domain engine.

    Accepts origin, destination, arrival time, preparation time, safety buffer,
    and optional weather condition. Returns recommended wake time, leave time,
    expected arrival time, and a transparent breakdown of all applied modifiers.

    Fetches live traffic durations from configured routing providers (Google/Mapbox).
    If routing fails, falls back to Haversine heuristic with reduced confidence.
    """
    return await eta_service.calculate(payload)


@router.post(
    "/preview",
    response_model=ETAPreviewResponse,
    summary="ETA Live Preview (No Auth)",
    tags=["ETA Engine"],
    dependencies=[Depends(rate_limit_dependency(prefix="eta_preview"))],
)
async def preview_eta(
    payload: ETAPreviewRequest,
    routing_service: RoutingService = Depends(get_routing_service),
) -> ETAPreviewResponse:
    """
    Lightweight ETA preview for real-time form updates.

    Does NOT require authentication. Suitable for the CreateAlarmPage
    live preview panel. If the client has already calculated route durations,
    pass base_duration_seconds and traffic_duration_seconds to skip the
    server-side routing API call.
    """
    # Build ephemeral service for this request (no alarm_repo needed for preview)
    eta_service = ETACalculationService(routing_service=routing_service)
    return await eta_service.calculate_preview(payload)


@router.post(
    "/alarms/{alarm_id}/evaluate",
    response_model=AlarmETAUpdateResult,
    summary="Re-evaluate and Persist Alarm ETA",
    tags=["ETA Engine"],
    status_code=status.HTTP_200_OK,
)
async def evaluate_alarm_eta(
    alarm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    alarm_repo: AlarmRepository = Depends(get_alarm_repository),
    eta_service: ETACalculationService = Depends(get_eta_calculation_service),
) -> AlarmETAUpdateResult:
    """
    Re-evaluates ETA for a specific alarm and persists the calculated wake time,
    leave time, and travel metrics into the alarm record.

    Used by the AlarmDetailsPage and background evaluation workers.
    Returns the updated alarm ETA fields.
    """
    alarm = alarm_repo.get_by_user_and_id(current_user.id, alarm_id)
    if not alarm:
        raise NotFoundException("Alarm", alarm_id)

    if alarm.user_id != current_user.id:
        raise ForbiddenException("You do not have permission to evaluate this alarm.")

    return await eta_service.evaluate_alarm(alarm)
