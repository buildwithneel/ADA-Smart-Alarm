from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_personalization_service
from app.models.user import User
from app.schemas.assistant import PersonalizationResponse, PersonalizationUpdate
from app.services.personalization_service import PersonalizationService

logger = logging.getLogger("ada.api.personalization")

router = APIRouter()


@router.get(
    "",
    response_model=PersonalizationResponse,
    summary="Get Personalization Preferences",
)
def get_personalization(
    current_user: User = Depends(get_current_user),
    service: PersonalizationService = Depends(get_personalization_service),
) -> PersonalizationResponse:
    """Returns transparent view of authenticated user's personalization defaults."""
    return service.get_personalization(current_user.id)


@router.patch(
    "",
    response_model=PersonalizationResponse,
    summary="Update Personalization Preferences",
)
def update_personalization(
    data: PersonalizationUpdate,
    current_user: User = Depends(get_current_user),
    service: PersonalizationService = Depends(get_personalization_service),
) -> PersonalizationResponse:
    """Updates user-controlled personalization preferences."""
    return service.update_personalization(current_user.id, data)


@router.post(
    "/reset",
    response_model=PersonalizationResponse,
    summary="Reset Personalization to Defaults",
)
def reset_personalization(
    current_user: User = Depends(get_current_user),
    service: PersonalizationService = Depends(get_personalization_service),
) -> PersonalizationResponse:
    """Resets all personalization settings back to system defaults."""
    return service.reset_personalization(current_user.id)
