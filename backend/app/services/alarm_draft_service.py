from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional, Tuple
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import ConflictException, NotFoundException, ValidationException
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.assistant import AlarmDraft, DraftStatus
from app.models.destination import Destination, DestinationType
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.destination_repository import DestinationRepository
from app.schemas.alarm import AlarmCreate, AlarmResponse
from app.schemas.assistant import (
    AlarmDraftResponse,
    AlarmDraftUpdateRequest,
    ParsedIntent,
)
from app.schemas.destination import DestinationCreate
from app.services.alarm_service import AlarmService
from app.services.base import BaseService
from app.services.eta_engine import ETACalculationEngine
from app.services.geocoding_service import GeocodingService
from app.services.routing_service import RoutingService

logger = logging.getLogger("ada.services.alarm_draft")


class AlarmDraftService(BaseService):
    """
    Deterministic Alarm Draft Service.
    Orchestrates the creation, deterministic ETA calculation, inline editing,
    and explicit user confirmation of Smart Alarm Drafts.
    """

    def __init__(
        self,
        assistant_repo: AssistantRepository,
        destination_repo: DestinationRepository,
        alarm_repo: AlarmRepository,
        alarm_service: AlarmService,
        geocoding_service: Optional[GeocodingService] = None,
        routing_service: Optional[RoutingService] = None,
    ):
        self.assistant_repo = assistant_repo
        self.destination_repo = destination_repo
        self.alarm_repo = alarm_repo
        self.alarm_service = alarm_service
        self.geocoding_service = geocoding_service or GeocodingService()
        self.routing_service = routing_service or RoutingService()

    # ------------------------------------------------------------------
    # Draft Generation & Schedule Calculation
    # ------------------------------------------------------------------

    async def create_draft_from_intent(
        self,
        user_id: uuid.UUID,
        intent: ParsedIntent,
        conversation_id: Optional[uuid.UUID] = None,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
    ) -> AlarmDraft:
        """
        Creates an Alarm Draft and computes the deterministic schedule.
        NEVER creates an active alarm.
        """
        tz = self._resolve_timezone(intent.timezone)
        now_in_tz = datetime.now(tz=tz)

        # 1. Resolve Destination
        dest_id, dest_address, dest_lat, dest_lng = await self._resolve_destination(
            user_id=user_id,
            destination_text=intent.destination_text or "Unspecified Destination",
            destination_place_id=intent.destination_place_id,
        )

        # 2. Date and Time Defaults
        target_date = intent.arrival_date or (now_in_tz + timedelta(days=1)).date()
        target_time = intent.required_arrival_time or time(hour=9, minute=0)

        prep_time = intent.preparation_duration_minutes if intent.preparation_duration_minutes is not None else 30
        buffer_time = intent.safety_buffer_minutes if intent.safety_buffer_minutes is not None else 15
        mode = intent.transport_mode or TransportMode.DRIVING

        # 3. Compute Deterministic Schedule
        (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
        ) = await self._calculate_schedule(
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            target_date=target_date,
            target_time=target_time,
            prep_time=prep_time,
            safety_buffer=buffer_time,
            mode=mode,
            tz=tz,
        )

        title = intent.title or (
            f"Arrival at {intent.destination_text.strip().title()}"
            if intent.destination_text
            else "Smart Alarm Draft"
        )

        explanation = self._build_grounded_explanation(
            destination_text=intent.destination_text or "your destination",
            arrival_time_str=target_time.strftime("%I:%M %p"),
            leave_time_str=leave_dt.strftime("%I:%M %p"),
            wake_time_str=wake_dt.strftime("%I:%M %p"),
            travel_mins=travel_mins,
            traffic_delay_mins=traffic_delay_mins,
            safety_buffer=buffer_time,
            prep_time=prep_time,
        )

        draft = AlarmDraft(
            id=uuid.uuid4(),
            user_id=user_id,
            conversation_id=conversation_id,
            title=title,
            destination_text=intent.destination_text or "Unspecified Destination",
            destination_id=dest_id,
            destination_address=dest_address,
            destination_lat=dest_lat,
            destination_lng=dest_lng,
            arrival_time=target_time,
            arrival_date=target_date,
            preparation_time=prep_time,
            safety_buffer=buffer_time,
            transportation_mode=mode,
            timezone=intent.timezone or "Asia/Kolkata",
            calculated_wake_time=wake_dt,
            calculated_leave_time=leave_dt,
            planned_arrival_time=planned_arrival_dt,
            travel_duration_minutes=travel_mins,
            traffic_delay_minutes=traffic_delay_mins,
            status=DraftStatus.DRAFT,
            explanation=explanation,
        )

        created = self.assistant_repo.create_draft(draft)
        logger.info(f"Alarm Draft created: ID={created.id} for user {user_id}")
        return created

    # ------------------------------------------------------------------
    # Draft CRUD & Inline Editing
    # ------------------------------------------------------------------

    def get_draft(self, user_id: uuid.UUID, draft_id: uuid.UUID) -> AlarmDraft:
        draft = self.assistant_repo.get_draft(user_id, draft_id)
        if not draft:
            # Check IDOR
            raw_draft = self.assistant_repo.get_any_draft_for_audit(draft_id)
            if raw_draft and raw_draft.user_id != user_id:
                logger.warning(
                    f"IDOR detected: User {user_id} attempted access to draft {draft_id} owned by {raw_draft.user_id}"
                )
            raise NotFoundException("Draft", draft_id)
        return draft

    async def update_draft(
        self,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
        data: AlarmDraftUpdateRequest,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
    ) -> AlarmDraft:
        draft = self.get_draft(user_id, draft_id)

        if draft.status != DraftStatus.DRAFT:
            raise ValidationException(f"Cannot edit draft with status '{draft.status.value}'.")

        # Apply updates
        if data.title is not None:
            draft.title = data.title.strip()

        if data.destination_text is not None and data.destination_text.strip() != draft.destination_text:
            draft.destination_text = data.destination_text.strip()
            dest_id, dest_address, dest_lat, dest_lng = await self._resolve_destination(
                user_id=user_id,
                destination_text=draft.destination_text,
            )
            draft.destination_id = dest_id
            draft.destination_address = dest_address
            draft.destination_lat = dest_lat
            draft.destination_lng = dest_lng

        if data.arrival_time is not None:
            draft.arrival_time = data.arrival_time
        if data.arrival_date is not None:
            draft.arrival_date = data.arrival_date
        if data.preparation_time is not None:
            draft.preparation_time = data.preparation_time
        if data.safety_buffer is not None:
            draft.safety_buffer = data.safety_buffer
        if data.transportation_mode is not None:
            draft.transportation_mode = data.transportation_mode
        if data.timezone is not None:
            draft.timezone = data.timezone

        tz = self._resolve_timezone(draft.timezone)

        # Recalculate schedule
        (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
        ) = await self._calculate_schedule(
            dest_lat=draft.destination_lat,
            dest_lng=draft.destination_lng,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            target_date=draft.arrival_date or (datetime.now(tz=tz) + timedelta(days=1)).date(),
            target_time=draft.arrival_time,
            prep_time=draft.preparation_time,
            safety_buffer=draft.safety_buffer,
            mode=draft.transportation_mode,
            tz=tz,
        )

        draft.calculated_wake_time = wake_dt
        draft.calculated_leave_time = leave_dt
        draft.planned_arrival_time = planned_arrival_dt
        draft.travel_duration_minutes = travel_mins
        draft.traffic_delay_minutes = traffic_delay_mins

        draft.explanation = self._build_grounded_explanation(
            destination_text=draft.destination_text,
            arrival_time_str=draft.arrival_time.strftime("%I:%M %p"),
            leave_time_str=leave_dt.strftime("%I:%M %p"),
            wake_time_str=wake_dt.strftime("%I:%M %p"),
            travel_mins=travel_mins,
            traffic_delay_mins=traffic_delay_mins,
            safety_buffer=draft.safety_buffer,
            prep_time=draft.preparation_time,
        )

        updated = self.assistant_repo.update_draft(draft)
        logger.info(f"Alarm Draft {draft_id} updated and recalculated.")
        return updated

    def discard_draft(self, user_id: uuid.UUID, draft_id: uuid.UUID) -> AlarmDraft:
        draft = self.get_draft(user_id, draft_id)
        draft.status = DraftStatus.DISCARDED
        updated = self.assistant_repo.update_draft(draft)
        logger.info(f"Alarm Draft {draft_id} discarded by user {user_id}")
        return updated

    # ------------------------------------------------------------------
    # Explicit User Confirmation -> Alarm Creation
    # ------------------------------------------------------------------

    async def confirm_draft(
        self,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
        idempotency_key: Optional[str] = None,
    ) -> AlarmResponse:
        """
        Converts the reviewed Alarm Draft into a live, scheduled Smart Alarm.
        Requires explicit user action. Revalidates all constraints.
        """
        draft = self.get_draft(user_id, draft_id)

        if draft.status == DraftStatus.CONFIRMED:
            raise ConflictException("This alarm draft has already been confirmed and scheduled.")

        if draft.status == DraftStatus.DISCARDED:
            raise ValidationException("Cannot confirm a discarded draft.")

        # Re-verify arrival time is in the future
        tz = self._resolve_timezone(draft.timezone)
        now_in_tz = datetime.now(tz=tz)
        target_date = draft.arrival_date or (now_in_tz + timedelta(days=1)).date()
        target_arrival_dt = datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=draft.arrival_time.hour,
            minute=draft.arrival_time.minute,
            second=draft.arrival_time.second,
            tzinfo=tz,
        )

        if target_arrival_dt <= now_in_tz:
            raise ValidationException("Arrival time cannot be in the past. Please update the draft arrival time.")

        # Ensure destination entity exists in user's destinations
        dest_id = draft.destination_id
        if not dest_id:
            # Create a user destination record
            new_dest = self.destination_repo.create_for_user(
                user_id=user_id,
                obj_in=DestinationCreate(
                    name=draft.destination_text[:100],
                    type=DestinationType.CUSTOM,
                    latitude=draft.destination_lat or 22.5996,
                    longitude=draft.destination_lng or 72.8205,
                    address=draft.destination_address or draft.destination_text,
                ),
            )
            dest_id = new_dest.id
            draft.destination_id = dest_id

        # Use the existing AlarmService to create and schedule the alarm
        alarm_create = AlarmCreate(
            title=draft.title,
            destination_id=dest_id,
            arrival_time=draft.arrival_time,
            arrival_date=draft.arrival_date,
            preparation_time=draft.preparation_time,
            safety_buffer=draft.safety_buffer,
            transportation_mode=draft.transportation_mode,
            timezone=draft.timezone,
            enabled=True,
        )

        idem_key = idempotency_key or f"draft-confirm:{draft.id}"

        # Call existing AlarmService.create_alarm
        alarm_resp = await self.alarm_service.create_alarm(
            user_id=user_id,
            data=alarm_create,
            idempotency_key=idem_key,
        )

        # Mark draft as confirmed
        draft.status = DraftStatus.CONFIRMED
        draft.idempotency_key = idem_key
        self.assistant_repo.update_draft(draft)

        logger.info(f"Alarm Draft {draft.id} successfully confirmed -> Alarm {alarm_resp.id} scheduled.")
        return alarm_resp

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    async def _resolve_destination(
        self,
        user_id: uuid.UUID,
        destination_text: str,
        destination_place_id: Optional[str] = None,
    ) -> Tuple[Optional[uuid.UUID], Optional[str], Optional[float], Optional[float]]:
        """Resolves destination coordinates via existing user places or geocoding."""
        # Check if place ID is an existing destination UUID
        if destination_place_id:
            try:
                dest_uuid = uuid.UUID(destination_place_id)
                dest = self.destination_repo.get_by_user_and_id(user_id, dest_uuid)
                if dest:
                    return dest.id, dest.address, dest.latitude, dest.longitude
            except ValueError:
                pass

        # Check existing user destinations by name match
        saved_dests = self.destination_repo.get_by_user(user_id, skip=0, limit=50)
        cleaned_text = destination_text.strip().lower()
        for d in saved_dests:
            if d.name.lower() in cleaned_text or cleaned_text in d.name.lower():
                return d.id, d.address, d.latitude, d.longitude

        # Geocode the destination text via existing geocoding service
        try:
            results = await self.geocoding_service.search(destination_text, limit=1)
            if results:
                top = results[0]
                return None, top.formatted_address, top.latitude, top.longitude
        except Exception as exc:
            logger.warning(f"Geocoding search failed for '{destination_text}': {exc}")

        # Fallback default coordinates (CHARUSAT / Central Gujarat coordinates for testing)
        return None, destination_text, 22.5996, 72.8205

    async def _calculate_schedule(
        self,
        dest_lat: Optional[float],
        dest_lng: Optional[float],
        origin_lat: Optional[float],
        origin_lng: Optional[float],
        target_date: date,
        target_time: time,
        prep_time: int,
        safety_buffer: int,
        mode: TransportMode,
        tz: ZoneInfo,
    ) -> Tuple[datetime, datetime, datetime, int, int]:
        """
        Executes ADA's deterministic formula:
        plannedArrivalTime = requiredArrivalTime - safetyBuffer
        recommendedLeaveTime = plannedArrivalTime - travelDuration
        recommendedWakeTime = recommendedLeaveTime - preparationDuration
        """
        target_arrival_dt = datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            tzinfo=tz,
        )

        d_lat = dest_lat or 22.5996
        d_lng = dest_lng or 72.8205
        o_lat = origin_lat if origin_lat is not None else 23.2156
        o_lng = origin_lng if origin_lng is not None else 72.6369

        base_secs = 2100  # Default 35 mins
        traffic_secs = 2100

        try:
            from app.services.eta_calculation_service import ETACalculationService
            travel_mode = ETACalculationService._map_transport_mode(mode.value)
            route = await self.routing_service.calculate_route(
                origin_lat=o_lat,
                origin_lng=o_lng,
                dest_lat=d_lat,
                dest_lng=d_lng,
                mode=travel_mode,
            )
            base_secs = route.duration_seconds
            traffic_secs = route.traffic_duration_seconds
        except Exception as exc:
            logger.debug(f"Routing call fell back to heuristic: {exc}")
            base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                o_lat, o_lng, d_lat, d_lng, mode
            )

        travel_mins = max(1, traffic_secs // 60)
        base_mins = max(1, base_secs // 60)
        traffic_delay_mins = max(0, travel_mins - base_mins)

        # Precise schedule math
        planned_arrival_dt = target_arrival_dt - timedelta(minutes=safety_buffer)
        leave_dt = planned_arrival_dt - timedelta(minutes=travel_mins)
        wake_dt = leave_dt - timedelta(minutes=prep_time)

        return (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
        )

    def _build_grounded_explanation(
        self,
        destination_text: str,
        arrival_time_str: str,
        leave_time_str: str,
        wake_time_str: str,
        travel_mins: int,
        traffic_delay_mins: int,
        safety_buffer: int,
        prep_time: int,
    ) -> str:
        traffic_str = f" (including {traffic_delay_mins} min traffic delay)" if traffic_delay_mins > 0 else ""
        return (
            f"Here is your recommended schedule to reach {destination_text} by {arrival_time_str}:\n"
            f"• Planned Arrival: {arrival_time_str} with a {safety_buffer}-minute safety buffer.\n"
            f"• Leave Time: {leave_time_str} ({travel_mins} min travel duration{traffic_str}).\n"
            f"• Wake-up Time: {wake_time_str} ({prep_time} min preparation routine).\n"
            f"No alarm has been created yet. Please review and confirm below."
        )

    @staticmethod
    def _resolve_timezone(tz_name: Optional[str]) -> ZoneInfo:
        if not tz_name:
            return ZoneInfo("Asia/Kolkata")
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            return ZoneInfo("Asia/Kolkata")
