from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.services.calendar.base import CalendarEventData, CalendarProvider

logger = logging.getLogger("ada.calendar.google")


class GoogleCalendarProvider(CalendarProvider):
    """
    Google Calendar OAuth 2.0 Provider.
    Enforces least-privilege read-only events scope:
    'https://www.googleapis.com/auth/calendar.events.readonly'
    """

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or settings.GOOGLE_CALENDAR_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CALENDAR_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.GOOGLE_CALENDAR_REDIRECT_URI

    @property
    def provider_name(self) -> str:
        return "google"

    def get_authorization_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """
        Builds Google OAuth 2.0 authorization redirect URL requesting least-privilege scope.
        """
        if not self.client_id:
            raise RuntimeError("GOOGLE_CALENDAR_CLIENT_ID not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "response_type": "code",
            "scope": f"{self.READONLY_SCOPE} email",
            "access_type": "offline",
            "prompt": "consent",  # Ensures refresh token is returned
            "state": state,
            "include_granted_scopes": "true",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self, code: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchanges the authorization code for access and refresh tokens.
        Also retrieves the connected account email.
        """
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Google Calendar OAuth credentials not configured")

        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            res = await client.post(self.TOKEN_URL, data=payload)
            if res.status_code != 200:
                logger.error(f"Google token exchange failed: {res.status_code} - {res.text}")
                raise RuntimeError("Failed to exchange authorization code with Google")

            tokens = res.json()
            access_token = tokens.get("access_token")

            # Fetch account email for identification
            email = "unknown@google.com"
            try:
                user_res = await client.get(
                    self.USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_res.status_code == 200:
                    email = user_res.json().get("email", email)
            except Exception as exc:
                logger.warning(f"Could not retrieve user email from Google: {exc}")

            expires_in = tokens.get("expires_in", 3600)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            return {
                "access_token": access_token,
                "refresh_token": tokens.get("refresh_token"),
                "token_expires_at": token_expires_at,
                "account_email": email,
                "scope": tokens.get("scope", self.READONLY_SCOPE),
            }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes expired access token.
        """
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Google Calendar OAuth credentials not configured")

        payload = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            res = await client.post(self.TOKEN_URL, data=payload)
            if res.status_code != 200:
                logger.error(f"Google token refresh failed: {res.status_code} - {res.text}")
                raise RuntimeError("Failed to refresh Google access token")

            tokens = res.json()
            expires_in = tokens.get("expires_in", 3600)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            return {
                "access_token": tokens.get("access_token"),
                "token_expires_at": token_expires_at,
            }

    async def list_upcoming_events(
        self, access_token: str, time_min: datetime, time_max: datetime
    ) -> List[CalendarEventData]:
        """
        Retrieves user's upcoming events from Google Calendar.
        Converts all times to timezone-aware datetimes.
        """
        # Ensure UTC ISO format
        min_utc = time_min.astimezone(timezone.utc) if time_min.tzinfo else time_min.replace(tzinfo=timezone.utc)
        max_utc = time_max.astimezone(timezone.utc) if time_max.tzinfo else time_max.replace(tzinfo=timezone.utc)

        params = {
            "timeMin": min_utc.isoformat(),
            "timeMax": max_utc.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        }

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            res = await client.get(self.EVENTS_URL, params=params, headers=headers)
            if res.status_code == 401:
                raise PermissionError("Google Calendar access token expired or revoked")
            elif res.status_code != 200:
                logger.error(f"Google Calendar events API error: {res.status_code} - {res.text}")
                raise RuntimeError(f"Google Calendar events error: {res.status_code}")

            data = res.json()
            items = data.get("items", [])
            results: List[CalendarEventData] = []

            for item in items:
                try:
                    event = self._parse_event(item)
                    if event:
                        results.append(event)
                except Exception as exc:
                    logger.warning(f"Skipping unparseable calendar event: {exc}")

            return results

    async def revoke_token(self, token: str) -> bool:
        """
        Revokes token with Google OAuth service.
        """
        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                res = await client.post(self.REVOKE_URL, params={"token": token})
                return res.status_code == 200
        except Exception as exc:
            logger.warning(f"Google token revocation request failed: {exc}")
            return False

    def _parse_event(self, item: Dict[str, Any]) -> Optional[CalendarEventData]:
        ext_id = item.get("id")
        if not ext_id:
            return None

        summary = item.get("summary", "Untitled Event").strip() or "Untitled Event"
        location = item.get("location")
        status = item.get("status", "confirmed")

        start = item.get("start", {})
        end = item.get("end", {})

        is_all_day = False
        tz_str = start.get("timeZone", "UTC")

        if "dateTime" in start:
            start_dt = datetime.fromisoformat(start["dateTime"])
            end_dt = datetime.fromisoformat(end.get("dateTime", start["dateTime"]))
        elif "date" in start:
            is_all_day = True
            # All day events: YYYY-MM-DD
            d = datetime.strptime(start["date"], "%Y-%m-%d").date()
            start_dt = datetime(d.year, d.month, d.day, 9, 0, tzinfo=timezone.utc)
            end_d = datetime.strptime(end.get("date", start["date"]), "%Y-%m-%d").date()
            end_dt = datetime(end_d.year, end_d.month, end_d.day, 17, 0, tzinfo=timezone.utc)
        else:
            return None

        # Ensure timezone awareness
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        return CalendarEventData(
            external_event_id=ext_id,
            title=summary[:255],
            start_time=start_dt,
            end_time=end_dt,
            timezone=tz_str,
            location=location[:500] if location else None,
            all_day=is_all_day,
            status=status,
            event_link=item.get("htmlLink"),
            source_provider="google",
        )
