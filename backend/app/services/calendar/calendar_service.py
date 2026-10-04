from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.errors import ForbiddenException, NotFoundException, ValidationException
from app.core.events import AlarmEvent, AlarmEventType, publish_alarm_event
from app.models.alarm import Alarm, TransportMode
from app.models.calendar import CalendarConnection, CalendarEvent
from app.models.destination import Destination, DestinationType
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.alarm import AlarmCreate
from app.services.alarm_recalculation_service import AlarmRecalculationService
from app.services.alarm_service import AlarmService
from app.services.calendar.base import CalendarEventData, CalendarProvider
from app.services.calendar.google_calendar_provider import GoogleCalendarProvider
from app.services.geocoding_service import GeocodingService

logger = logging.getLogger("ada.services.calendar")


class CalendarService:
    """
    Step 10 Calendar Integration Service.
    Coordinates least-privilege OAuth, encrypted token storage at rest,
    event synchronization, calendar-based alarm creation, and event change reconciliation.
    """

    def __init__(
        self,
        calendar_repo: CalendarRepository,
        alarm_repo: AlarmRepository,
        destination_repo: DestinationRepository,
        pref_repo: PreferenceRepository,
        provider: Optional[CalendarProvider] = None,
        geocoding_service: Optional[GeocodingService] = None,
    ):
        self.calendar_repo = calendar_repo
        self.alarm_repo = alarm_repo
        self.destination_repo = destination_repo
        self.pref_repo = pref_repo
        self.provider = provider or GoogleCalendarProvider()
        self.geocoding_service = geocoding_service or GeocodingService()

    # ------------------------------------------------------------------
    # OAuth Connection Lifecycle
    # ------------------------------------------------------------------

    def get_authorization_url(self, user_id: uuid.UUID, redirect_uri: Optional[str] = None) -> str:
        """
        Generates OAuth 2.0 authorization URL with least-privilege readonly scope.
        The state parameter carries the user ID.
        """
        state = f"ada-cal:{user_id}"
        return self.provider.get_authorization_url(state=state, redirect_uri=redirect_uri)

    async def handle_oauth_callback(
        self, user_id: uuid.UUID, code: str, state: str, redirect_uri: Optional[str] = None
    ) -> CalendarConnection:
        """
        Exchanges code for tokens, encrypts tokens with Fernet, and saves connection.
        """
        # Validate state
        if not state.startswith("ada-cal:") or state.split("ada-cal:")[1] != str(user_id):
            raise ValidationException("Invalid OAuth state parameter. Request rejected.")

        token_data = await self.provider.exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        account_email = token_data.get("account_email", "unknown@google.com")
        token_expires_at = token_data.get("token_expires_at")
        scopes = token_data.get("scope", "https://www.googleapis.com/auth/calendar.events.readonly")

        if not access_token:
            raise ValidationException("OAuth provider did not return an access token.")

        # Encrypt sensitive tokens at rest
        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(refresh_token) if refresh_token else None

        # Check existing connection
        existing = self.calendar_repo.get_connection_by_user(user_id, self.provider.provider_name)
        if existing:
            existing.encrypted_access_token = enc_access
            if enc_refresh:
                existing.encrypted_refresh_token = enc_refresh
            existing.token_expires_at = token_expires_at
            existing.account_email = account_email
            existing.is_active = True
            existing.sync_status = "idle"
            conn = self.calendar_repo.update_connection(existing)
        else:
            conn = self.calendar_repo.create_connection(
                user_id=user_id,
                account_email=account_email,
                encrypted_access_token=enc_access,
                encrypted_refresh_token=enc_refresh,
                token_expires_at=token_expires_at,
                provider=self.provider.provider_name,
                scopes=scopes,
            )

        # Trigger immediate background sync
        try:
            await self.sync_connection_events(conn.id)
        except Exception as exc:
            logger.warning(f"Initial calendar sync encountered error: {exc}")

        return conn

    async def disconnect_calendar(self, connection_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Revokes token with provider and deletes local calendar connection & events.
        """
        conn = self.calendar_repo.get_connection(connection_id)
        if not conn:
            raise NotFoundException("Calendar connection not found.")
        if conn.user_id != user_id:
            raise ForbiddenException("You do not own this calendar connection.")

        # Best-effort external token revocation
        try:
            if conn.encrypted_access_token:
                raw_token = decrypt_token(conn.encrypted_access_token)
                await self.provider.revoke_token(raw_token)
        except Exception as exc:
            logger.warning(f"Provider token revocation warning: {exc}")

        return self.calendar_repo.delete_connection(connection_id)

    # ------------------------------------------------------------------
    # Event Synchronization
    # ------------------------------------------------------------------

    async def sync_connection_events(self, connection_id: uuid.UUID) -> Dict[str, Any]:
        """
        Synchronizes upcoming calendar events for an active connection.
        Handles automatic token refresh if expired.
        Reconciles linked alarm changes.
        """
        conn = self.calendar_repo.get_connection(connection_id)
        if not conn or not conn.is_active:
            return {"status": "skipped", "reason": "Connection inactive or not found"}

        now = datetime.now(timezone.utc)
        conn.sync_status = "syncing"
        self.calendar_repo.update_connection(conn)

        try:
            # 1. Check token expiry & refresh if needed
            access_token = decrypt_token(conn.encrypted_access_token)
            token_exp = conn.token_expires_at
            if token_exp and token_exp.tzinfo is None:
                token_exp = token_exp.replace(tzinfo=timezone.utc)
            if token_exp and token_exp <= now:
                if not conn.encrypted_refresh_token:
                    conn.sync_status = "error"
                    conn.error_message = "Access token expired and no refresh token available. Reconnection required."
                    self.calendar_repo.update_connection(conn)
                    return {"status": "error", "error": "Token expired"}

                raw_refresh = decrypt_token(conn.encrypted_refresh_token)
                refreshed = await self.provider.refresh_access_token(raw_refresh)
                access_token = refreshed["access_token"]
                conn.encrypted_access_token = encrypt_token(access_token)
                conn.token_expires_at = refreshed.get("token_expires_at")
                self.calendar_repo.update_connection(conn)

            # 2. Query provider for events in window [now, now + 7 days]
            window_days = settings.CALENDAR_UPCOMING_WINDOW_DAYS
            time_max = now + timedelta(days=window_days)
            events_data = await self.provider.list_upcoming_events(
                access_token=access_token, time_min=now, time_max=time_max
            )

            synced_count = 0
            created_count = 0
            updated_count = 0

            for ev_data in events_data:
                # Check if existing event was linked to an alarm
                existing_ev = self.calendar_repo.get_event_by_external_id(
                    conn.id, ev_data.external_event_id
                )
                prev_start = existing_ev.start_time if existing_ev else None
                prev_status = existing_ev.status if existing_ev else None

                event, was_created = self.calendar_repo.upsert_event(
                    connection_id=conn.id,
                    user_id=conn.user_id,
                    external_event_id=ev_data.external_event_id,
                    title=ev_data.title,
                    start_time=ev_data.start_time,
                    end_time=ev_data.end_time,
                    timezone_str=ev_data.timezone,
                    location=ev_data.location,
                    all_day=ev_data.all_day,
                    status=ev_data.status,
                    source_provider=ev_data.source_provider,
                    event_link=ev_data.event_link,
                )
                synced_count += 1
                if was_created:
                    created_count += 1
                else:
                    updated_count += 1

                # 3. Reconcile linked alarm if event changed
                if existing_ev and existing_ev.alarm_id:
                    # Restore alarm link on updated model
                    event.alarm_id = existing_ev.alarm_id
                    self.calendar_repo.db.commit()
                    await self._reconcile_event_change(
                        event=event,
                        prev_start=prev_start,
                        prev_status=prev_status,
                    )

            conn.last_synced_at = now
            conn.sync_status = "success"
            conn.error_message = None
            self.calendar_repo.update_connection(conn)

            return {
                "status": "success",
                "synced_count": synced_count,
                "created_count": created_count,
                "updated_count": updated_count,
            }

        except Exception as exc:
            logger.error(f"Error during calendar sync for connection {connection_id}: {exc}", exc_info=True)
            conn.sync_status = "error"
            conn.error_message = str(exc)[:500]
            self.calendar_repo.update_connection(conn)
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Calendar-to-Alarm Creation Flow
    # ------------------------------------------------------------------

    async def propose_alarm_from_event(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Validates event, resolves location, and proposes schedule for user review.
        """
        event = self.calendar_repo.get_event(event_id)
        if not event:
            raise NotFoundException("Calendar event not found.")
        if event.user_id != user_id:
            raise ForbiddenException("You do not own this calendar event.")

        # Check existing linked alarm
        if event.alarm_id:
            existing_alarm = self.alarm_repo.get(event.alarm_id)
            if existing_alarm and existing_alarm.enabled:
                return {
                    "already_linked": True,
                    "alarm_id": str(existing_alarm.id),
                    "alarm_title": existing_alarm.title,
                }

        # Resolve location
        resolved_lat = event.resolved_latitude
        resolved_lng = event.resolved_longitude
        destination_name = event.location or "Calendar Destination"

        if (resolved_lat is None or resolved_lng is None) and event.location:
            try:
                geo_results = await self.geocoding_service.search(
                    query=event.location, limit=1
                )
                if geo_results:
                    resolved_lat = geo_results[0].latitude
                    resolved_lng = geo_results[0].longitude
                    event.resolved_latitude = resolved_lat
                    event.resolved_longitude = resolved_lng
                    self.calendar_repo.db.commit()
            except Exception as exc:
                logger.warning(f"Could not geocode event location '{event.location}': {exc}")

        # Retrieve user preference defaults
        pref = self.pref_repo.get_by_user_id(user_id)
        prep_time = pref.default_preparation_time if pref else 30
        safety_buffer = pref.default_safety_buffer if pref else 15
        mode = pref.default_transportation.value if pref else "driving"

        target_dt = event.start_time
        arrival_time_str = target_dt.strftime("%H:%M:%S")
        arrival_date_str = target_dt.strftime("%Y-%m-%d")

        has_usable_location = resolved_lat is not None and resolved_lng is not None

        return {
            "event_id": str(event.id),
            "event_title": event.title,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "timezone": event.timezone,
            "location": event.location,
            "has_usable_location": has_usable_location,
            "resolved_latitude": resolved_lat,
            "resolved_longitude": resolved_lng,
            "proposed_arrival_time": arrival_time_str,
            "proposed_arrival_date": arrival_date_str,
            "preparation_time": prep_time,
            "safety_buffer": safety_buffer,
            "transportation_mode": mode,
        }

    async def create_alarm_from_event(
        self,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        destination_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        preparation_time: Optional[int] = None,
        safety_buffer: Optional[int] = None,
        transportation_mode: Optional[str] = None,
    ) -> Alarm:
        """
        Creates an Alarm linked to the calendar event after user review and confirmation.
        """
        event = self.calendar_repo.get_event(event_id)
        if not event:
            raise NotFoundException("Calendar event not found.")
        if event.user_id != user_id:
            raise ForbiddenException("You do not own this calendar event.")

        # Resolve destination
        dest: Optional[Destination] = None
        if destination_id:
            dest = self.destination_repo.get(destination_id)
            if not dest or dest.user_id != user_id:
                raise NotFoundException("Selected destination not found or not owned by user.")
        elif event.resolved_latitude is not None and event.resolved_longitude is not None:
            # Create a destination record from the resolved event location
            dest = self.destination_repo.create(
                user_id=user_id,
                name=event.location or event.title,
                latitude=event.resolved_latitude,
                longitude=event.resolved_longitude,
                address=event.location,
                type=DestinationType.CUSTOM,
                provider="calendar",
            )
        else:
            raise ValidationException(
                "Event has no resolved coordinates. Please specify a destination."
            )

        # User preferences
        pref = self.pref_repo.get_by_user_id(user_id)
        p_time = preparation_time or (pref.default_preparation_time if pref else 30)
        s_buffer = safety_buffer or (pref.default_safety_buffer if pref else 15)
        t_mode = transportation_mode or (pref.default_transportation.value if pref else "driving")

        alarm_title = title or f"Calendar: {event.title}"

        # Target arrival time from event start time
        arr_time = event.start_time.time()
        arr_date = event.start_time.date()

        alarm_service = AlarmService(self.alarm_repo, self.destination_repo)
        create_payload = AlarmCreate(
            title=alarm_title,
            destination_id=dest.id,
            arrival_time=arr_time,
            arrival_date=arr_date,
            preparation_time=p_time,
            safety_buffer=s_buffer,
            transportation_mode=TransportMode(t_mode),
            timezone=event.timezone if event.timezone != "UTC" else (pref.user.timezone if pref and pref.user else "Asia/Kolkata"),
        )

        alarm = await alarm_service.create_alarm(
            user_id=user_id,
            data=create_payload,
        )

        # Link alarm and calendar event
        alarm.calendar_event_id = event.external_event_id
        self.alarm_repo.db.commit()
        self.calendar_repo.link_alarm_to_event(event.id, alarm.id)

        # Emit domain event
        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.CALENDAR_ALARM_CREATED,
                alarm_id=str(alarm.id),
                user_id=str(user_id),
                payload={
                    "event_id": str(event.id),
                    "external_event_id": event.external_event_id,
                    "event_title": event.title,
                    "wake_time": alarm.calculated_wake_time.isoformat() if alarm.calculated_wake_time else None,
                },
            )
        )

        return alarm

    # ------------------------------------------------------------------
    # Event Change Reconciliation
    # ------------------------------------------------------------------

    async def _reconcile_event_change(
        self,
        event: CalendarEvent,
        prev_start: Optional[datetime],
        prev_status: Optional[str],
    ) -> None:
        """
        Reconciles updates when an authorized calendar event changes time or is cancelled.
        """
        if not event.alarm_id:
            return

        alarm = self.alarm_repo.get(event.alarm_id)
        if not alarm or not alarm.enabled:
            return

        user_pref = self.pref_repo.get_by_user_id(alarm.user_id)
        auto_reschedule = user_pref.calendar_auto_reschedule if user_pref else False

        # 1. Event was cancelled
        if event.status == "cancelled" and prev_status != "cancelled":
            logger.info(f"Calendar event {event.external_event_id} was cancelled. Linked alarm: {alarm.id}")
            publish_alarm_event(
                AlarmEvent(
                    event_type=AlarmEventType.CALENDAR_EVENT_CHANGED,
                    alarm_id=str(alarm.id),
                    user_id=str(alarm.user_id),
                    payload={
                        "change_type": "event_cancelled",
                        "event_id": str(event.id),
                        "external_event_id": event.external_event_id,
                        "title": event.title,
                        "action_required": "confirm_cancellation",
                    },
                )
            )
            return

        # 2. Event start time changed
        if prev_start and event.start_time != prev_start:
            logger.info(
                f"Calendar event {event.external_event_id} time changed: {prev_start} -> {event.start_time}"
            )

            if auto_reschedule:
                # Automatically recalculate schedule with the new arrival time
                try:
                    alarm.arrival_time = event.start_time.time()
                    self.alarm_repo.db.commit()

                    recalc_service = AlarmRecalculationService(
                        self.alarm_repo, self.destination_repo
                    )
                    res = await recalc_service.recalculate_alarm(
                        alarm_id=alarm.id,
                        user_id=alarm.user_id,
                        force=True,
                    )
                    logger.info(f"Alarm {alarm.id} automatically recalculated due to calendar event change: {res.status}")
                except Exception as exc:
                    logger.error(f"Failed to auto-reschedule alarm {alarm.id}: {exc}")
            else:
                # Informational alert: user confirmation required
                publish_alarm_event(
                    AlarmEvent(
                        event_type=AlarmEventType.CALENDAR_EVENT_CHANGED,
                        alarm_id=str(alarm.id),
                        user_id=str(alarm.user_id),
                        payload={
                            "change_type": "time_changed",
                            "event_id": str(event.id),
                            "previous_start_time": prev_start.isoformat(),
                            "new_start_time": event.start_time.isoformat(),
                            "auto_reschedule_applied": False,
                            "action_required": "confirm_reschedule",
                        },
                    )
                )
