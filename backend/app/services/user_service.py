import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.errors import NotFoundException
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.preference import UserPreferenceResponse, UserPreferenceUpdate
from app.schemas.user import UserResponse
from app.services.base import BaseService


class UserService(BaseService):
    """Business service orchestrating User profiles and preference configurations."""

    def __init__(
        self,
        user_repo: UserRepository,
        preference_repo: PreferenceRepository,
    ):
        self.user_repo = user_repo
        self.preference_repo = preference_repo

    def get_user_profile(self, user_id: uuid.UUID) -> UserResponse:
        user = self.user_repo.get_with_preference(user_id)
        if not user:
            raise NotFoundException("User", user_id)
        return UserResponse.model_validate(user)

    def update_preferences(
        self, user_id: uuid.UUID, data: UserPreferenceUpdate
    ) -> UserPreferenceResponse:
        pref = self.preference_repo.update_preference(user_id, data)
        return UserPreferenceResponse.model_validate(pref)

    def export_user_data(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        GDPR Data Portability export:
        Retrieves all user-owned profile data, preferences, destinations, and alarms in a structured JSON format.
        """
        user = self.user_repo.get_with_preference(user_id)
        if not user:
            raise NotFoundException("User", user_id)

        destinations = [
            {
                "id": str(d.id),
                "name": d.name,
                "address": d.address,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "is_favorite": d.is_favorite,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in getattr(user, "destinations", [])
        ]
        alarms = [
            {
                "id": str(a.id),
                "title": a.title,
                "target_arrival_time": a.target_arrival_time.isoformat() if a.target_arrival_time else None,
                "calculated_wake_time": a.calculated_wake_time.isoformat() if a.calculated_wake_time else None,
                "calculated_leave_time": a.calculated_leave_time.isoformat() if a.calculated_leave_time else None,
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "is_active": a.is_active,
                "transport_mode": a.transport_mode.value if hasattr(a.transport_mode, "value") else str(a.transport_mode),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in getattr(user, "alarms", [])
        ]
        pref = user.preference
        pref_data = (
            {
                "default_transportation": pref.default_transportation,
                "default_preparation_time": pref.default_preparation_time,
                "default_safety_buffer": pref.default_safety_buffer,
            }
            if pref
            else {}
        )

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "timezone": user.timezone,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "preferences": pref_data,
            "destinations": destinations,
            "alarms": alarms,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def delete_user_account(self, user_id: uuid.UUID) -> bool:
        """
        GDPR Right to be Forgotten:
        Deletes the user and cascades deletion to all user-owned records.
        """
        user = self.user_repo.get(user_id)
        if not user:
            raise NotFoundException("User", user_id)
        self.user_repo.delete(user_id)
        return True

