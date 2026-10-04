from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import uuid

from app.core.config import settings
from app.core.errors import ValidationException
from app.integrations.ai.factory import get_ai_provider
from app.integrations.ai.interface import AIProviderInterface
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.assistant import ParsedIntent

logger = logging.getLogger("ada.services.intent_parser")


class IntentParser:
    """
    Orchestrates natural-language intent parsing, user personalization merging,
    and prompt-injection sanitization.
    """

    def __init__(
        self,
        ai_provider: Optional[AIProviderInterface] = None,
        pref_repo: Optional[PreferenceRepository] = None,
        dest_repo: Optional[DestinationRepository] = None,
    ):
        self.ai_provider = ai_provider or get_ai_provider()
        self.pref_repo = pref_repo
        self.dest_repo = dest_repo

    async def parse(
        self,
        prompt: str,
        user_id: uuid.UUID,
        client_timezone: Optional[str] = None,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
    ) -> ParsedIntent:
        cleaned_prompt = prompt.strip()
        max_len = getattr(settings, "AI_MAX_INPUT_LENGTH", 1000)
        if len(cleaned_prompt) > max_len:
            raise ValidationException(f"Message exceeds maximum allowed length of {max_len} characters.")

        # Build context for the AI parser
        user_context: Dict[str, Any] = {
            "timezone": client_timezone or "Asia/Kolkata",
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
        }

        # Retrieve user personalization defaults
        if self.pref_repo:
            pref = self.pref_repo.get_by_user(user_id)
            if pref:
                user_context["default_preparation_time"] = pref.default_preparation_time
                user_context["default_safety_buffer"] = pref.default_safety_buffer
                user_context["default_transportation"] = pref.default_transportation.value
                user_context["assistant_response_style"] = pref.assistant_response_style
                user_context["use_alarm_history_suggestions"] = pref.use_alarm_history_suggestions

        # Retrieve saved user destination names for fast matching
        if self.dest_repo:
            destinations = self.dest_repo.get_by_user(user_id, skip=0, limit=20)
            user_context["saved_destinations"] = [
                {"id": str(d.id), "name": d.name, "address": d.address}
                for d in destinations
            ]

        parsed = await self.ai_provider.parse_intent(cleaned_prompt, user_context)

        # Match destination to existing user destination if name is identical
        if parsed.destination_text and self.dest_repo:
            cleaned_dest = parsed.destination_text.lower()
            for d in user_context.get("saved_destinations", []):
                if d["name"].lower() in cleaned_dest or cleaned_dest in d["name"].lower():
                    parsed.destination_place_id = d["id"]
                    break

        return parsed
