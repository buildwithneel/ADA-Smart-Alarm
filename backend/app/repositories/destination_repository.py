import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.destination import Destination
from app.repositories.base import BaseRepository
from app.schemas.destination import DestinationCreate, DestinationUpdate


class DestinationRepository(BaseRepository[Destination]):
    """Repository handling Destination entity persistence and queries."""

    def __init__(self, db: Session):
        super().__init__(Destination, db)

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Destination]:
        stmt = (
            select(Destination)
            .where(Destination.user_id == user_id)
            .order_by(Destination.is_favorite.desc(), Destination.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_user_and_id(
        self, user_id: uuid.UUID, destination_id: uuid.UUID
    ) -> Optional[Destination]:
        stmt = select(Destination).where(
            Destination.user_id == user_id,
            Destination.id == destination_id,
        )
        return self.db.scalars(stmt).first()

    def create_for_user(
        self, user_id: uuid.UUID, obj_in: DestinationCreate
    ) -> Destination:
        data = obj_in.model_dump()
        destination = Destination(user_id=user_id, **data)
        return self.create(destination)

    def update_destination(
        self, destination: Destination, obj_in: DestinationUpdate
    ) -> Destination:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(destination, field, value)
        return self.update(destination)
