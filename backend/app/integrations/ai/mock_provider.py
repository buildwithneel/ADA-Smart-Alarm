from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.integrations.ai.interface import AIProviderInterface
from app.models.alarm import TransportMode
from app.schemas.assistant import IntentType, ParsedIntent

logger = logging.getLogger("ada.ai.mock")

# Keywords that suggest schedule explanation query
EXPLANATION_PATTERNS = [
    r"\bwhy\b",
    r"\bexplain\b",
    r"\breason\b",
    r"\bhow come\b",
]

# Keywords that suggest an update to an existing draft
UPDATE_PATTERNS = [
    r"\bchange (?:the )?(?:buffer|prep|time|destination)\b",
    r"\bupdate (?:the )?(?:buffer|prep|time|destination)\b",
    r"\bmake (?:the )?buffer\b",
    r"\bmove my wake-?up\b",
    r"\badd (?:a )?\d+-minute buffer\b",
    r"\bneed \d+ minutes to get ready\b",
]

# Dangerous prompt-injection signatures
INJECTION_SIGNATURES = [
    r"ignore (?:all )?previous instructions",
    r"system prompt",
    r"bypass (?:user )?confirmation",
    r"confirm (?:the )?alarm directly",
    r"as an admin",
    r"drop table",
    r"delete from",
]


class MockAIProvider(AIProviderInterface):
    """
    Deterministic, zero-cost AI Provider.
    Implements production-grade regex and heuristic natural-language intent parsing.
    Requires no external API keys, has zero external latency, and adheres strictly
    to ADA's safety rules against hallucinations and prompt injection.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    async def health_check(self) -> bool:
        return True

    async def parse_intent(
        self, prompt: str, user_context: Dict[str, Any]
    ) -> ParsedIntent:
        cleaned_prompt = prompt.strip()
        tz_name = user_context.get("timezone") or "Asia/Kolkata"
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            tz = ZoneInfo("Asia/Kolkata")

        now_in_tz = datetime.now(tz=tz)

        # 1. Prompt-Injection Inspection
        for sig in INJECTION_SIGNATURES:
            if re.search(sig, cleaned_prompt, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected and neutralized: {sig}")
                return ParsedIntent(
                    intent_type=IntentType.GENERAL_QUERY,
                    explanation="I cannot bypass confirmation or execute system instructions. All alarms require explicit user confirmation.",
                    confidence=0.1,
                )

        # 2. Check for Explanation Requests
        for p in EXPLANATION_PATTERNS:
            if re.search(p, cleaned_prompt, re.IGNORECASE):
                return ParsedIntent(
                    intent_type=IntentType.EXPLAIN_SCHEDULE,
                    explanation="Schedule explanation requested.",
                    confidence=0.95,
                )

        # 3. Check for Draft Update Requests
        creation_keywords = [
            r"\bwake me up\b",
            r"\breach\b",
            r"\barrive\b",
            r"\bmeeting\b",
            r"\bcreate\b",
            r"\bnew alarm\b",
        ]
        has_creation_intent = any(
            re.search(kw, cleaned_prompt, re.IGNORECASE) for kw in creation_keywords
        )
        is_update = False
        if not has_creation_intent:
            for p in UPDATE_PATTERNS:
                if re.search(p, cleaned_prompt, re.IGNORECASE):
                    is_update = True
                    break

        # 4. Extract Parameters
        dest_text = self._extract_destination(cleaned_prompt)
        arr_time, is_time_ambiguous = self._extract_time(cleaned_prompt)
        arr_date = self._extract_date(cleaned_prompt, now_in_tz)
        prep_time = self._extract_prep_time(cleaned_prompt)
        buffer_time = self._extract_buffer_time(cleaned_prompt)
        mode = self._extract_transport_mode(cleaned_prompt)

        missing_fields: List[str] = []
        ambiguities: List[str] = []

        # If it's a new alarm request, check required fields
        if not is_update:
            if not dest_text:
                missing_fields.append("destination")
            if arr_time is None:
                if is_time_ambiguous:
                    ambiguities.append("Time was mentioned without AM/PM or 24-hour clarity (e.g., '9' vs '9 AM').")
                    missing_fields.append("arrival_time_clarification")
                else:
                    missing_fields.append("arrival_time")

        # Check for past arrival time
        if arr_time and arr_date:
            target_dt = datetime(
                year=arr_date.year,
                month=arr_date.month,
                day=arr_date.day,
                hour=arr_time.hour,
                minute=arr_time.minute,
                second=arr_time.second,
                tzinfo=tz,
            )
            if target_dt < now_in_tz:
                ambiguities.append(f"Target arrival time ({target_dt.strftime('%Y-%m-%d %H:%M')}) is in the past.")
                missing_fields.append("future_arrival_time")

        # Fall back to user personalization defaults for missing optional values
        if prep_time is None:
            prep_time = user_context.get("default_preparation_time", 30)
        if buffer_time is None:
            buffer_time = user_context.get("default_safety_buffer", 15)
        if mode is None:
            default_mode_str = user_context.get("default_transportation", "driving")
            try:
                mode = TransportMode(default_mode_str)
            except ValueError:
                mode = TransportMode.DRIVING

        # Generate descriptive title
        title = None
        if dest_text:
            title = f"Arrival at {dest_text.strip().title()}"
        elif is_update:
            title = "Updated Smart Alarm"

        intent_type = IntentType.UPDATE_DRAFT if is_update else IntentType.CREATE_ALARM
        if missing_fields or ambiguities:
            intent_type = IntentType.ASK_CLARIFICATION

        confidence = 0.95 if not missing_fields else 0.60

        return ParsedIntent(
            intent_type=intent_type,
            title=title,
            destination_text=dest_text,
            required_arrival_time=arr_time,
            arrival_date=arr_date,
            timezone=tz_name,
            preparation_duration_minutes=prep_time,
            safety_buffer_minutes=buffer_time,
            transport_mode=mode,
            missing_fields=missing_fields,
            ambiguities=ambiguities,
            confidence=confidence,
        )

    async def generate_explanation(
        self, schedule_data: Dict[str, Any], prompt: str, user_context: Dict[str, Any]
    ) -> str:
        """
        Builds a grounded, strictly data-driven explanation without hallucinations.
        """
        arr_str = schedule_data.get("arrival_time", "your required time")
        leave_str = schedule_data.get("leave_time", "departure time")
        wake_str = schedule_data.get("wake_time", "wake-up time")
        travel_mins = schedule_data.get("travel_duration_minutes", 0)
        safety_mins = schedule_data.get("safety_buffer", 0)
        prep_mins = schedule_data.get("preparation_time", 0)
        dest_name = schedule_data.get("destination_text", "your destination")
        traffic_delay = schedule_data.get("traffic_delay_minutes", 0)

        traffic_note = f" (including {traffic_delay} min of traffic)" if traffic_delay > 0 else ""

        explanation = (
            f"To reach {dest_name} by {arr_str}:\n"
            f"• Leave at {leave_str} based on a {travel_mins}-minute travel duration{traffic_note} "
            f"and your {safety_mins}-minute safety buffer.\n"
            f"• Wake up at {wake_str} to allow {prep_mins} minutes for your morning routine."
        )

        weather_note = schedule_data.get("weather_note")
        if weather_note:
            explanation += f"\n• Context: {weather_note}"

        return explanation

    # ------------------------------------------------------------------
    # Extraction Helpers
    # ------------------------------------------------------------------

    def _extract_destination(self, text: str) -> Optional[str]:
        # Regex patterns to capture destination name
        patterns = [
            r"\breach\s+([A-Za-z0-9\s,\-\.\']+?)\s+by\s+\d+",
            r"\breach\s+([A-Za-z0-9\s,\-\.\']+?)\s+(?:tomorrow|today|at\s+\d+|on\s+)",
            r"\bgo\s+to\s+([A-Za-z0-9\s,\-\.\']+?)\s+by\s+\d+",
            r"\bgo\s+to\s+([A-Za-z0-9\s,\-\.\']+?)\s+(?:tomorrow|today|at\s+\d+|on\s+)",
            r"\bmeeting\s+at\s+(?:(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+at\s+)?([A-Za-z0-9\s,\-\.\']+?)(?:\.|$|,|tomorrow|today)",
            r"\bheading\s+to\s+([A-Za-z0-9\s,\-\.\']+?)(?:\.|$|,|by|at)",
            r"\bat\s+(?:my\s+)?([A-Za-z0-9\s,\-\.\']+?)(?:\.|$|,|by|tomorrow)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # Clean filler words
                candidate = re.sub(
                    r"\b(early enough|tomorrow morning|tomorrow afternoon|today|tomorrow)\b",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip()
                if candidate and len(candidate) >= 2 and not candidate.lower().startswith("9 am"):
                    return candidate

        # Fallback check for known landmarks or capitalized names
        charusat_match = re.search(r"\b(CHARUSAT(?:\s+University)?)\b", text, re.IGNORECASE)
        if charusat_match:
            return charusat_match.group(1)

        office_match = re.search(r"\b(office|college|airport|work|station)\b", text, re.IGNORECASE)
        if office_match:
            return office_match.group(1).title()

        return None

    def _extract_time(self, text: str) -> tuple[Optional[time], bool]:
        """
        Returns (extracted_time, is_ambiguous).
        Detects both explicit AM/PM and ambiguous unadorned digits (e.g. 'by 9').
        """
        # Explicit AM/PM or HH:MM matches
        explicit_patterns = [
            r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b",
            r"\b(\d{1,2})\s*(am|pm)\b",
            r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
        ]

        for idx, pat in enumerate(explicit_patterns):
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                if idx == 0:  # e.g. 9:30 AM
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    meridiem = match.group(3).lower()
                    if meridiem == "pm" and hour < 12:
                        hour += 12
                    elif meridiem == "am" and hour == 12:
                        hour = 0
                    return time(hour=hour, minute=minute), False
                elif idx == 1:  # e.g. 9 AM
                    hour = int(match.group(1))
                    minute = 0
                    meridiem = match.group(2).lower()
                    if meridiem == "pm" and hour < 12:
                        hour += 12
                    elif meridiem == "am" and hour == 12:
                        hour = 0
                    return time(hour=hour, minute=minute), False
                elif idx == 2:  # 24-hour HH:MM, e.g. 14:00 or 09:00
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    return time(hour=hour, minute=minute), False

        # Check for ambiguous time: e.g. "by 9", "at 9", "reach by 8" without AM/PM
        ambiguous_match = re.search(r"\b(?:by|at|reach by)\s+(\d{1,2})\b(?!\s*(?:am|pm|min|minute))", text, re.IGNORECASE)
        if ambiguous_match:
            return None, True

        return None, False

    def _extract_date(self, text: str, now_in_tz: datetime) -> Optional[date]:
        lowered = text.lower()
        if "tomorrow" in lowered:
            return (now_in_tz + timedelta(days=1)).date()
        if "day after tomorrow" in lowered:
            return (now_in_tz + timedelta(days=2)).date()
        if "today" in lowered:
            return now_in_tz.date()

        # Check ISO format YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
        if iso_match:
            try:
                return date(
                    int(iso_match.group(1)),
                    int(iso_match.group(2)),
                    int(iso_match.group(3)),
                )
            except ValueError:
                pass

        # If tomorrow morning or specific hour that is earlier than now, default to tomorrow
        return (now_in_tz + timedelta(days=1)).date()

    def _extract_prep_time(self, text: str) -> Optional[int]:
        patterns = [
            r"(\d+)\s*(?:m|min|mins|minute|minutes)\s*(?:to get ready|preparation|prep|routine)",
            r"(?:preparation|prep|routine|ready in)\s*(?:of\s*)?(\d+)\s*(?:m|min|mins|minute|minutes)?",
            r"takes me\s*(\d+)\s*(?:m|min|mins|minute|minutes)\s*to get ready",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                mins = int(match.group(1))
                if 0 <= mins <= 360:
                    return mins
        return None

    def _extract_buffer_time(self, text: str) -> Optional[int]:
        patterns = [
            r"(\d+)\s*(?:m|min|mins|minute|minutes)?\s*(?:safety\s*)?buffer",
            r"buffer\s*(?:of\s*)?(\d+)\s*(?:m|min|mins|minute|minutes)?",
            r"add\s*(?:a\s*)?(\d+)\s*(?:m|min|mins|minute|minutes)\s*buffer",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                mins = int(match.group(1))
                if 0 <= mins <= 180:
                    return mins
        return None

    def _extract_transport_mode(self, text: str) -> Optional[TransportMode]:
        lowered = text.lower()
        if any(w in lowered for w in ["transit", "bus", "train", "metro", "subway"]):
            return TransportMode.TRANSIT
        if any(w in lowered for w in ["bike", "bicycling", "cycle", "cycling"]):
            return TransportMode.BICYCLING
        if any(w in lowered for w in ["walk", "walking", "on foot"]):
            return TransportMode.WALKING
        if any(w in lowered for w in ["drive", "driving", "by car"]):
            return TransportMode.DRIVING
        return None
