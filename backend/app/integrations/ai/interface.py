from __future__ import annotations

import abc
from typing import Any, Dict

from app.schemas.assistant import ParsedIntent


class AIProviderInterface(abc.ABC):
    """
    Abstract AI Provider Interface.
    Enforces complete decoupling between external LLM providers and ADA domain logic.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier of the AI provider (e.g. 'gemini', 'mock')."""
        pass

    @abc.abstractmethod
    async def parse_intent(
        self, prompt: str, user_context: Dict[str, Any]
    ) -> ParsedIntent:
        """
        Parses a natural-language user prompt into a validated ParsedIntent schema.
        Must never invent unsupported facts.
        """
        pass

    @abc.abstractmethod
    async def generate_explanation(
        self, schedule_data: Dict[str, Any], prompt: str, user_context: Dict[str, Any]
    ) -> str:
        """
        Generates a grounded, data-backed explanation for the calculated schedule.
        """
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Checks if the provider is healthy and configured."""
        pass
