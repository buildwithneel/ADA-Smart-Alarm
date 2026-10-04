import uuid
from typing import List

from app.core.errors import NotFoundException
from app.repositories.destination_repository import DestinationRepository
from app.schemas.destination import (
    DestinationCreate,
    DestinationResponse,
    DestinationUpdate,
)
from app.services.base import BaseService


class DestinationService(BaseService):
    """Business service orchestrating Destination lifecycle and operations."""

    def __init__(self, destination_repo: DestinationRepository):
        self.destination_repo = destination_repo

    def list_destinations(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[DestinationResponse]:
        destinations = self.destination_repo.get_by_user(
            user_id, skip=skip, limit=limit
        )
        return [DestinationResponse.model_validate(d) for d in destinations]

    def get_destination(
        self, user_id: uuid.UUID, destination_id: uuid.UUID
    ) -> DestinationResponse:
        destination = self.destination_repo.get_by_user_and_id(user_id, destination_id)
        if not destination:
            raise NotFoundException("Destination", destination_id)
        return DestinationResponse.model_validate(destination)

    def create_destination(
        self, user_id: uuid.UUID, data: DestinationCreate
    ) -> DestinationResponse:
        destination = self.destination_repo.create_for_user(user_id, data)
        return DestinationResponse.model_validate(destination)

    def update_destination(
        self, user_id: uuid.UUID, destination_id: uuid.UUID, data: DestinationUpdate
    ) -> DestinationResponse:
        destination = self.destination_repo.get_by_user_and_id(user_id, destination_id)
        if not destination:
            raise NotFoundException("Destination", destination_id)
        updated = self.destination_repo.update_destination(destination, data)
        return DestinationResponse.model_validate(updated)

    def delete_destination(self, user_id: uuid.UUID, destination_id: uuid.UUID) -> None:
        destination = self.destination_repo.get_by_user_and_id(user_id, destination_id)
        if not destination:
            raise NotFoundException("Destination", destination_id)
        self.destination_repo.delete(destination)
