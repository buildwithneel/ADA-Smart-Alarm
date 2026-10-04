from __future__ import annotations

import logging
import uuid

from app.core.errors import NotFoundException, ValidationException
from app.models.alarm import TransportMode
from app.models.preference import UserPreference
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.assistant import PersonalizationResponse, PersonalizationUpdate
from app.services.base import BaseService

logger = logging.getLogger("ada.services.personalization")


class PersonalizationService(BaseService):
    """Business service governing user-controlled AI and schedule personalization."""

    def __init__(
        self,
        preference_repo: PreferenceRepository,
        user_repo: UserRepository,
    ):
        self.preference_repo = preference_repo
        self.user_repo = user_repo

    def get_personalization(self, user_id: uuid.UUID) -> PersonalizationResponse:
        pref = self._get_or_create_pref(user_id)
        return self._to_response(pref)

    def update_personalization(
        self, user_id: uuid.UUID, data: PersonalizationUpdate
    ) -> PersonalizationResponse:
        pref = self._get_or_create_pref(user_id)

        # Validate values
        if data.default_preparation_time is not None:
            if not (0 <= data.default_preparation_time <= 360):
                raise ValidationException("Default preparation time must be between 0 and 360 minutes.")
            pref.default_preparation_time = data.default_preparation_time

        if data.default_safety_buffer is not None:
            if not (0 <= data.default_safety_buffer <= 180):
                raise ValidationException("Default safety buffer must be between 0 and 180 minutes.")
            pref.default_safety_buffer = data.default_safety_buffer

        if data.default_transportation is not None:
            pref.default_transportation = data.default_transportation

        if data.assistant_response_style is not None:
            style = data.assistant_response_style.strip().lower()
            if style not in {"concise", "detailed", "direct", "casual"}:
                raise ValidationException("Assistant response style must be one of: 'concise', 'detailed', 'direct', 'casual'.")
            pref.assistant_response_style = style

        if data.save_conversation_history is not None:
            pref.save_conversation_history = data.save_conversation_history

        if data.use_alarm_history_suggestions is not None:
            pref.use_alarm_history_suggestions = data.use_alarm_history_suggestions

        if data.weather_buffer_enabled is not None:
            pref.weather_buffer_enabled = data.weather_buffer_enabled

        if data.calendar_sync_enabled is not None:
            pref.calendar_sync_enabled = data.calendar_sync_enabled

        self.preference_repo.update(pref)
        logger.info(f"Personalization preferences updated for user {user_id}")
        return self._to_response(pref)

    def reset_personalization(self, user_id: uuid.UUID) -> PersonalizationResponse:
        """Resets user personalization preferences to factory default values."""
        pref = self._get_or_create_pref(user_id)
        pref.default_transportation = TransportMode.DRIVING
        pref.default_preparation_time = 30
        pref.default_safety_buffer = 15
        pref.assistant_response_style = "concise"
        pref.save_conversation_history = True
        pref.use_alarm_history_suggestions = True
        pref.weather_buffer_enabled = False
        pref.calendar_sync_enabled = True

        self.preference_repo.update(pref)
        logger.info(f"Personalization preferences reset to defaults for user {user_id}")
        return self._to_response(pref)

    def _get_or_create_pref(self, user_id: uuid.UUID) -> UserPreference:
        pref = self.preference_repo.get_by_user(user_id)
        if not pref:
            # Check user exists
            user = self.user_repo.get(user_id)
            if not user:
                raise NotFoundException("User", user_id)
            pref = UserPreference(user_id=user_id)
            self.preference_repo.create(pref)
        return pref

    @staticmethod
    def _to_response(pref: UserPreference) -> PersonalizationResponse:
        return PersonalizationResponse(
            user_id=pref.user_id,
            default_transportation=pref.default_transportation,
            default_preparation_time=pref.default_preparation_time,
            default_safety_buffer=pref.default_safety_buffer,
            assistant_response_style=pref.assistant_response_style,
            save_conversation_history=pref.save_conversation_history,
            use_alarm_history_suggestions=pref.use_alarm_history_suggestions,
            weather_buffer_enabled=pref.weather_buffer_enabled,
            calendar_sync_enabled=pref.calendar_sync_enabled,
        )
