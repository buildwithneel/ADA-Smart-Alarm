from __future__ import annotations

import logging

from app.core.config import settings
from app.integrations.ai.gemini_provider import GeminiAIProvider
from app.integrations.ai.interface import AIProviderInterface
from app.integrations.ai.mock_provider import MockAIProvider

logger = logging.getLogger("ada.ai.factory")

_ai_provider_instance: AIProviderInterface | None = None


def get_ai_provider() -> AIProviderInterface:
    """
    Factory function providing the configured AI provider singleton.
    Configured via settings.AI_PROVIDER ('mock', 'gemini').
    """
    global _ai_provider_instance
    if _ai_provider_instance is not None:
        return _ai_provider_instance

    provider_type = (getattr(settings, "AI_PROVIDER", "mock") or "mock").lower()

    if provider_type == "gemini":
        logger.info("Initializing Gemini AI Provider")
        _ai_provider_instance = GeminiAIProvider()
    else:
        logger.info("Initializing Mock Deterministic AI Provider")
        _ai_provider_instance = MockAIProvider()

    return _ai_provider_instance


def set_ai_provider(provider: AIProviderInterface) -> None:
    """Explicitly override provider (used for testing)."""
    global _ai_provider_instance
    _ai_provider_instance = provider
