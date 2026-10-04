from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.integrations.ai.interface import AIProviderInterface
from app.integrations.ai.mock_provider import MockAIProvider
from app.schemas.assistant import ParsedIntent

logger = logging.getLogger("ada.ai.gemini")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAIProvider(AIProviderInterface):
    """
    Production AI Provider integrating Google Gemini via async REST API.
    Enforces server-side credentials, structured JSON output, bounded retries,
    timeouts, and automatic fallback to MockAIProvider when unconfigured or offline.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        fallback_provider: Optional[AIProviderInterface] = None,
    ):
        self.api_key = api_key or getattr(settings, "AI_API_KEY", None)
        self.model_name = model_name or getattr(settings, "AI_MODEL_NAME", "gemini-1.5-flash")
        self.fallback = fallback_provider or MockAIProvider()
        self.timeout = getattr(settings, "AI_TIMEOUT_SECONDS", 10.0)
        self.max_retries = getattr(settings, "AI_MAX_RETRIES", 2)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def health_check(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def parse_intent(
        self, prompt: str, user_context: Dict[str, Any]
    ) -> ParsedIntent:
        if not self.api_key:
            logger.info("Gemini API key not configured. Falling back to deterministic NLP parser.")
            return await self.fallback.parse_intent(prompt, user_context)

        system_instruction = (
            "You are ADA's Intent Extraction Engine. Your task is to extract smart alarm scheduling parameters "
            "from the user prompt into a valid JSON object matching the requested schema. "
            "IMPORTANT RULES:\n"
            "1. Do NOT invent destinations, dates, or arrival times.\n"
            "2. If destination is missing, add 'destination' to missing_fields.\n"
            "3. If time is ambiguous (e.g. '9' without AM/PM), add 'arrival_time_clarification' to missing_fields.\n"
            "4. Return strictly valid JSON."
        )

        url = f"{GEMINI_API_URL}/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"System: {system_instruction}"},
                        {"text": f"User context: {json.dumps(user_context)}"},
                        {"text": f"User prompt: {prompt}"},
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        # Bounded retries
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                text_content = parts[0]["text"]
                                raw_dict = json.loads(text_content)
                                return ParsedIntent.model_validate(raw_dict)
                    logger.warning(
                        f"Gemini API returned status {resp.status_code}, falling back to mock provider."
                    )
                    break
            except Exception as exc:
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}): {exc}")
                if attempt == self.max_retries:
                    break

        logger.info("Falling back to deterministic mock provider following Gemini failure.")
        return await self.fallback.parse_intent(prompt, user_context)

    async def generate_explanation(
        self, schedule_data: Dict[str, Any], prompt: str, user_context: Dict[str, Any]
    ) -> str:
        # Fall back to grounded deterministic explanation to guarantee accuracy
        return await self.fallback.generate_explanation(schedule_data, prompt, user_context)
