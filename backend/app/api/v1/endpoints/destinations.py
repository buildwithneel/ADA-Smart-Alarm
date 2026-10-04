import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_destination_service
from app.models.user import User
from app.schemas.destination import (
    DestinationCreate,
    DestinationResponse,
    DestinationUpdate,
)
from app.services.destination_service import DestinationService

router = APIRouter()


@router.get(
    "",
    response_model=List[DestinationResponse],
    summary="List Saved Destinations",
    tags=["Destinations"],
)
def list_destinations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
) -> List[DestinationResponse]:
    """Retrieve all destinations saved by the authenticated user."""
    return destination_service.list_destinations(
        current_user.id, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=DestinationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Destination",
    tags=["Destinations"],
)
def create_destination(
    destination_in: DestinationCreate,
    current_user: User = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
) -> DestinationResponse:
    """Create a new destination for the current user."""
    return destination_service.create_destination(current_user.id, destination_in)


@router.get(
    "/{destination_id}",
    response_model=DestinationResponse,
    summary="Get Destination Details",
    tags=["Destinations"],
)
def get_destination(
    destination_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
) -> DestinationResponse:
    """Retrieve details of a specific destination by UUID."""
    return destination_service.get_destination(current_user.id, destination_id)


@router.patch(
    "/{destination_id}",
    response_model=DestinationResponse,
    summary="Update Destination",
    tags=["Destinations"],
)
def update_destination(
    destination_id: uuid.UUID,
    destination_in: DestinationUpdate,
    current_user: User = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
) -> DestinationResponse:
    """Update fields of an existing destination."""
    return destination_service.update_destination(
        current_user.id, destination_id, destination_in
    )


@router.delete(
    "/{destination_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Destination",
    tags=["Destinations"],
)
def delete_destination(
    destination_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
) -> None:
    """Delete a saved destination by UUID."""
    destination_service.delete_destination(current_user.id, destination_id)
