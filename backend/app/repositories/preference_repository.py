import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.preference import UserPreference
from app.repositories.base import BaseRepository
from app.schemas.preference import UserPreferenceUpdate


class PreferenceRepository(BaseRepository[UserPreference]):
    """Repository handling UserPreference entity operations."""

    def __init__(self, db: Session):
        super().__init__(UserPreference, db)

    def get_by_user(self, user_id: uuid.UUID) -> Optional[UserPreference]:
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        return self.db.scalars(stmt).first()

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[UserPreference]:
        return self.get_by_user(user_id)

    def update_preference(
        self, user_id: uuid.UUID, obj_in: UserPreferenceUpdate
    ) -> UserPreference:
        pref = self.get_by_user(user_id)
        if not pref:
            pref = UserPreference(user_id=user_id)
            self.db.add(pref)

        data = obj_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(pref, field, value)

        return self.update(pref)
