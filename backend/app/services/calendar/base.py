from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CalendarEventData(BaseModel):
    """
    Normalized calendar event representation from any external calendar provider.
    Enforces privacy and data minimization.
    """
    external_event_id: str
    title: str = "Calendar Event"
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    location: Optional[str] = None
    all_day: bool = False
    status: str = "confirmed"  # confirmed, tentative, cancelled
    event_link: Optional[str] = None
    source_provider: str = "google"
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class CalendarProvider(ABC):
    """
    Abstract interface for external calendar providers (e.g. Google Calendar, Outlook).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """Generates OAuth consent URL with least-privilege read-only scopes."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(
        self, code: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token using the stored refresh token."""
        pass

    @abstractmethod
    async def list_upcoming_events(
        self, access_token: str, time_min: datetime, time_max: datetime
    ) -> List[CalendarEventData]:
        """Retrieves user events within the requested time bounds."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revokes external authorization upon user disconnection."""
        pass
