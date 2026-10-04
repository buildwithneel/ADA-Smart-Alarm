from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.events import AlarmEvent, AlarmEventType, publish_alarm_event
from app.core.redis import get_redis_client
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.destination import Destination
from app.models.schedule import ScheduleType
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.schemas.alarm import AlarmCreate, AlarmResponse, AlarmUpdate
from app.schemas.eta import ETACalculateRequest
from app.services.base import BaseService
from app.services.eta_engine import (
    CONFIDENCE_GOOGLE_LIVE,
    CONFIDENCE_HEURISTIC,
    CONFIDENCE_MAPBOX_LIVE,
    ETACalculationEngine,
)
from app.services.routing_service import RoutingService

logger = logging.getLogger("ada.services.alarm")

# In-memory fallback for duplicate request debouncing if Redis is offline
_in_memory_locks: Dict[str, float] = {}

# Alarm State Transition Rules
VALID_STATE_TRANSITIONS: Dict[AlarmStatus, Set[AlarmStatus]] = {
    AlarmStatus.DRAFT: {AlarmStatus.SCHEDULED, AlarmStatus.CANCELLED},
    AlarmStatus.SCHEDULED: {
        AlarmStatus.DISABLED,
        AlarmStatus.EXPIRED,
        AlarmStatus.COMPLETED,
        AlarmStatus.CANCELLED,
        AlarmStatus.ERROR,
    },
    AlarmStatus.ACTIVE: {
        AlarmStatus.COMPLETED,
        AlarmStatus.DISABLED,
        AlarmStatus.CANCELLED,
        AlarmStatus.ERROR,
    },
    AlarmStatus.DISABLED: {AlarmStatus.SCHEDULED, AlarmStatus.CANCELLED},
    AlarmStatus.EXPIRED: {AlarmStatus.SCHEDULED, AlarmStatus.CANCELLED},
    AlarmStatus.COMPLETED: {AlarmStatus.SCHEDULED, AlarmStatus.CANCELLED},
    AlarmStatus.ERROR: {AlarmStatus.SCHEDULED, AlarmStatus.DISABLED, AlarmStatus.CANCELLED},
    AlarmStatus.CANCELLED: set(),
}


class AlarmService(BaseService):
    """
    Core Domain Service managing the lifecycle, scheduling, calculation,
    and state transitions of ADA Smart Adaptive Alarms.
    """

    def __init__(
        self,
        alarm_repo: AlarmRepository,
        destination_repo: DestinationRepository,
        routing_service: Optional[RoutingService] = None,
    ):
        self.alarm_repo = alarm_repo
        self.destination_repo = destination_repo
        self.routing_service = routing_service or RoutingService()

    # ------------------------------------------------------------------
    # Query Operations
    # ------------------------------------------------------------------

    def list_alarms(
        self,
        user_id: uuid.UUID,
        status: Optional[AlarmStatus] = None,
        filter_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AlarmResponse]:
        """Retrieve all smart alarms configured by the authenticated user."""
        alarms = self.alarm_repo.get_by_user(
            user_id=user_id,
            status=status,
            filter_type=filter_type,
            skip=skip,
            limit=limit,
        )
        return [AlarmResponse.model_validate(a) for a in alarms]

    def get_alarm(self, user_id: uuid.UUID, alarm_id: uuid.UUID) -> AlarmResponse:
        """Retrieve details and calculated schedule for a specific alarm by ID."""
        alarm = self._get_verified_alarm(user_id, alarm_id)
        return AlarmResponse.model_validate(alarm)

    # ------------------------------------------------------------------
    # Create Alarm Flow
    # ------------------------------------------------------------------

    async def create_alarm(
        self,
        user_id: uuid.UUID,
        data: AlarmCreate,
        idempotency_key: Optional[str] = None,
    ) -> AlarmResponse:
        """
        Creates a new Smart Adaptive Alarm:
        1. Protects against duplicate concurrent submissions.
        2. Validates destination exists and belongs to user.
        3. Validates arrival time is not in past (for one-time alarms).
        4. Validates routine and safety buffer constraints.
        5. Computes schedule (wake time, leave time, planned arrival) via ETA engine.
        6. Persists alarm with initial SCHEDULED or DISABLED state.
        7. Publishes ALARM_SCHEDULED domain event.
        """
        # 1. Concurrency / Duplicate submission guard
        self._acquire_idempotency_lock(user_id, data, idempotency_key)

        # 2. Verify destination belongs to authenticated user
        destination = self.destination_repo.get_by_user_and_id(user_id, data.destination_id)
        if not destination:
            logger.warning(
                f"Alarm creation rejected: Destination {data.destination_id} not found for user {user_id}"
            )
            raise NotFoundException("Destination", data.destination_id)

        # 3. Validate arrival time
        tz = self._resolve_timezone(data.timezone)
        target_arrival_dt = self._calculate_target_arrival_datetime(
            arrival_time=data.arrival_time,
            arrival_date=data.arrival_date,
            tz=tz,
        )

        now_in_tz = datetime.now(tz=tz)
        is_one_time = (
            data.schedule is None
            or data.schedule.schedule_type == ScheduleType.ONCE
            or data.arrival_date is not None
        )

        if is_one_time and target_arrival_dt <= now_in_tz:
            logger.warning(
                f"Alarm creation rejected: arrival time {target_arrival_dt} is in the past (now: {now_in_tz})"
            )
            raise ValidationException(
                "Arrival time cannot be in the past for a one-time alarm. Please select a future time."
            )

        # 4. Validate durations
        if data.preparation_time < 0 or data.preparation_time > 360:
            raise ValidationException("Preparation time must be between 0 and 360 minutes.")
        if data.safety_buffer < 0 or data.safety_buffer > 180:
            raise ValidationException("Safety buffer must be between 0 and 180 minutes.")

        # 5. Calculate Smart Alarm Schedule
        (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
            confidence,
        ) = await self._calculate_schedule_values(
            destination=destination,
            arrival_dt=target_arrival_dt,
            preparation_time=data.preparation_time,
            safety_buffer=data.safety_buffer,
            mode=data.transportation_mode,
            origin_lat=data.origin_lat,
            origin_lng=data.origin_lng,
            override_seconds=data.override_base_duration_seconds,
        )

        # 6. Set initial state based on enabled toggle
        initial_status = AlarmStatus.SCHEDULED if data.enabled else AlarmStatus.DISABLED

        # Persist alarm entity with schedule
        alarm = self.alarm_repo.create_with_schedule(user_id, data)

        # Update with dynamic schedule outputs
        alarm = self.alarm_repo.update_schedule_calculation(
            alarm=alarm,
            calculated_wake_time=wake_dt,
            calculated_leave_time=leave_dt,
            planned_arrival_time=planned_arrival_dt,
            current_travel_minutes=travel_mins,
            traffic_delay_minutes=traffic_delay_mins,
            calculation_version="eta-v1",
        )

        logger.info(
            f"Smart Alarm created: ID={alarm.id} | Wake={wake_dt.strftime('%H:%M')} | "
            f"Leave={leave_dt.strftime('%H:%M')} | Planned Arrival={planned_arrival_dt.strftime('%H:%M')}"
        )

        # 7. Publish domain event
        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.ALARM_SCHEDULED if data.enabled else AlarmEventType.ALARM_DISABLED,
                alarm_id=str(alarm.id),
                user_id=str(user_id),
                payload={
                    "title": alarm.title,
                    "destination_id": str(alarm.destination_id),
                    "wake_time": wake_dt.isoformat(),
                    "leave_time": leave_dt.isoformat(),
                    "planned_arrival": planned_arrival_dt.isoformat(),
                    "status": alarm.status.value,
                },
            )
        )

        return AlarmResponse.model_validate(alarm)

    # ------------------------------------------------------------------
    # Update Alarm Flow
    # ------------------------------------------------------------------

    async def update_alarm(
        self,
        user_id: uuid.UUID,
        alarm_id: uuid.UUID,
        data: AlarmUpdate,
    ) -> AlarmResponse:
        """
        Updates an existing Smart Alarm:
        - Verifies ownership.
        - If destination or schedule parameters change, recalculates schedule.
        - If enabled or status changes, applies and verifies valid state transition.
        """
        alarm = self._get_verified_alarm(user_id, alarm_id)

        # Check destination ownership if destination is changing
        if data.destination_id is not None and data.destination_id != alarm.destination_id:
            dest = self.destination_repo.get_by_user_and_id(user_id, data.destination_id)
            if not dest:
                raise NotFoundException("Destination", data.destination_id)
            destination = dest
        else:
            destination = alarm.destination

        # Handle explicit state transition
        if data.status is not None and data.status != alarm.status:
            self._validate_state_transition(alarm.status, data.status)
            alarm.status = data.status
            if data.status == AlarmStatus.SCHEDULED:
                alarm.enabled = True
            elif data.status in {AlarmStatus.DISABLED, AlarmStatus.EXPIRED, AlarmStatus.CANCELLED}:
                alarm.enabled = False

        if data.enabled is not None and data.enabled != alarm.enabled:
            target_status = AlarmStatus.SCHEDULED if data.enabled else AlarmStatus.DISABLED
            self._validate_state_transition(alarm.status, target_status)
            alarm.status = target_status
            alarm.enabled = data.enabled

        # Determine if schedule parameters changed
        dest_changed = data.destination_id is not None and data.destination_id != alarm.destination_id
        arrival_changed = data.arrival_time is not None and data.arrival_time != alarm.arrival_time
        prep_changed = data.preparation_time is not None and data.preparation_time != alarm.preparation_time
        buffer_changed = data.safety_buffer is not None and data.safety_buffer != alarm.safety_buffer
        mode_changed = data.transportation_mode is not None and data.transportation_mode != alarm.transportation_mode
        tz_changed = data.timezone is not None and data.timezone != alarm.timezone

        should_recalculate = (
            dest_changed or arrival_changed or prep_changed or buffer_changed or mode_changed or tz_changed
        )

        # Update base fields
        updated_alarm = self.alarm_repo.update_with_schedule(alarm, data)

        if should_recalculate:
            tz = self._resolve_timezone(updated_alarm.timezone)
            arrival_date = updated_alarm.schedule.specific_date if updated_alarm.schedule else None
            target_arrival_dt = self._calculate_target_arrival_datetime(
                arrival_time=updated_alarm.arrival_time,
                arrival_date=arrival_date,
                tz=tz,
            )

            # Preserve explicit override or existing travel duration if destination/mode unchanged
            override_secs = getattr(data, "override_base_duration_seconds", None)
            if override_secs is None and not dest_changed and not mode_changed and updated_alarm.current_travel_minutes:
                override_secs = updated_alarm.current_travel_minutes * 60

            (
                wake_dt,
                leave_dt,
                planned_arrival_dt,
                travel_mins,
                traffic_delay_mins,
                _,
            ) = await self._calculate_schedule_values(
                destination=destination,
                arrival_dt=target_arrival_dt,
                preparation_time=updated_alarm.preparation_time,
                safety_buffer=updated_alarm.safety_buffer,
                mode=updated_alarm.transportation_mode,
                origin_lat=updated_alarm.origin_lat,
                origin_lng=updated_alarm.origin_lng,
                override_seconds=override_secs,
            )

            updated_alarm = self.alarm_repo.update_schedule_calculation(
                alarm=updated_alarm,
                calculated_wake_time=wake_dt,
                calculated_leave_time=leave_dt,
                planned_arrival_time=planned_arrival_dt,
                current_travel_minutes=travel_mins,
                traffic_delay_minutes=traffic_delay_mins,
                calculation_version="eta-v1",
            )

        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.ALARM_UPDATED,
                alarm_id=str(updated_alarm.id),
                user_id=str(user_id),
                payload={"title": updated_alarm.title, "status": updated_alarm.status.value},
            )
        )

        return AlarmResponse.model_validate(updated_alarm)

    # ------------------------------------------------------------------
    # Enable / Disable Operations
    # ------------------------------------------------------------------

    async def enable_alarm(self, user_id: uuid.UUID, alarm_id: uuid.UUID) -> AlarmResponse:
        """Enables a smart alarm, transitioning status to SCHEDULED and refreshing schedule."""
        alarm = self._get_verified_alarm(user_id, alarm_id)
        self._validate_state_transition(alarm.status, AlarmStatus.SCHEDULED)

        tz = self._resolve_timezone(alarm.timezone)
        arrival_date = alarm.schedule.specific_date if alarm.schedule else None
        target_arrival_dt = self._calculate_target_arrival_datetime(
            arrival_time=alarm.arrival_time,
            arrival_date=arrival_date,
            tz=tz,
        )

        now_in_tz = datetime.now(tz=tz)
        is_one_time = (
            alarm.schedule is None
            or alarm.schedule.schedule_type == ScheduleType.ONCE
            or arrival_date is not None
        )
        if is_one_time and target_arrival_dt <= now_in_tz:
            raise ValidationException(
                "Cannot enable alarm: arrival time is in the past. Please update the arrival time first."
            )

        # Refresh schedule calculation
        (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
            _,
        ) = await self._calculate_schedule_values(
            destination=alarm.destination,
            arrival_dt=target_arrival_dt,
            preparation_time=alarm.preparation_time,
            safety_buffer=alarm.safety_buffer,
            mode=alarm.transportation_mode,
            origin_lat=alarm.origin_lat,
            origin_lng=alarm.origin_lng,
        )

        alarm.enabled = True
        alarm.status = AlarmStatus.SCHEDULED
        alarm = self.alarm_repo.update_schedule_calculation(
            alarm=alarm,
            calculated_wake_time=wake_dt,
            calculated_leave_time=leave_dt,
            planned_arrival_time=planned_arrival_dt,
            current_travel_minutes=travel_mins,
            traffic_delay_minutes=traffic_delay_mins,
            calculation_version="eta-v1",
        )

        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.ALARM_SCHEDULED,
                alarm_id=str(alarm.id),
                user_id=str(user_id),
            )
        )

        return AlarmResponse.model_validate(alarm)

    def disable_alarm(self, user_id: uuid.UUID, alarm_id: uuid.UUID) -> AlarmResponse:
        """Disables an alarm, preventing future trigger checks."""
        alarm = self._get_verified_alarm(user_id, alarm_id)
        self._validate_state_transition(alarm.status, AlarmStatus.DISABLED)

        alarm.enabled = False
        alarm.status = AlarmStatus.DISABLED
        self.alarm_repo.db.commit()
        self.alarm_repo.db.refresh(alarm)

        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.ALARM_DISABLED,
                alarm_id=str(alarm.id),
                user_id=str(user_id),
            )
        )

        return AlarmResponse.model_validate(alarm)

    # ------------------------------------------------------------------
    # Delete Operation
    # ------------------------------------------------------------------

    def delete_alarm(self, user_id: uuid.UUID, alarm_id: uuid.UUID) -> None:
        """Deletes an alarm safely, ensuring cross-user authorization."""
        alarm = self._get_verified_alarm(user_id, alarm_id)
        self.alarm_repo.delete(alarm)

        publish_alarm_event(
            AlarmEvent(
                event_type=AlarmEventType.ALARM_CANCELLED,
                alarm_id=str(alarm_id),
                user_id=str(user_id),
            )
        )

    # ------------------------------------------------------------------
    # Duplicate Operation
    # ------------------------------------------------------------------

    async def duplicate_alarm(
        self,
        user_id: uuid.UUID,
        alarm_id: uuid.UUID,
        new_title: Optional[str] = None,
    ) -> AlarmResponse:
        """
        Duplicates an existing alarm into a new independent record with its own UUID.
        """
        original = self._get_verified_alarm(user_id, alarm_id)

        title = new_title or f"{original.title} (Copy)"
        dup_data = AlarmCreate(
            title=title,
            destination_id=original.destination_id,
            arrival_time=original.arrival_time,
            preparation_time=original.preparation_time,
            safety_buffer=original.safety_buffer,
            transportation_mode=original.transportation_mode,
            enabled=original.enabled,
            timezone=original.timezone,
            origin_lat=original.origin_lat,
            origin_lng=original.origin_lng,
            override_base_duration_seconds=(original.current_travel_minutes * 60) if original.current_travel_minutes else None,
            schedule=original.schedule,
        )

        dup_idem_key = f"duplicate:{alarm_id}:{uuid.uuid4()}"
        return await self.create_alarm(user_id, dup_data, idempotency_key=dup_idem_key)

    # ------------------------------------------------------------------
    # Refresh Calculation Operation
    # ------------------------------------------------------------------

    async def refresh_calculation(
        self, user_id: uuid.UUID, alarm_id: uuid.UUID
    ) -> AlarmResponse:
        """
        Re-evaluates live route and recomputes ETA and schedule for the alarm.
        Delegates to AlarmRecalculationService for unified domain calculation.
        """
        from app.services.alarm_recalculation_service import AlarmRecalculationService

        recalc_svc = AlarmRecalculationService(
            alarm_repo=self.alarm_repo,
            destination_repo=self.destination_repo,
            routing_service=self.routing_service,
        )
        res = await recalc_svc.recalculate_alarm(alarm_id=alarm_id, user_id=user_id, force=True)
        if res.status == "not_found":
            raise NotFoundException("Alarm", alarm_id)
        updated_alarm = self.alarm_repo.get_by_user_and_id(user_id, alarm_id)
        if not updated_alarm:
            raise NotFoundException("Alarm", alarm_id)
        return AlarmResponse.model_validate(updated_alarm)

    # ------------------------------------------------------------------
    # Expired Alarm Handling
    # ------------------------------------------------------------------

    def mark_expired_alarms(self) -> int:
        """
        Scans all scheduled alarms and marks one-time alarms whose arrival
        time has passed as EXPIRED.
        """
        active_alarms = self.alarm_repo.get_active_alarms_for_evaluation(limit=500)
        expired_count = 0

        for alarm in active_alarms:
            is_one_time = (
                alarm.schedule is None
                or alarm.schedule.schedule_type == ScheduleType.ONCE
                or (alarm.schedule and alarm.schedule.specific_date is not None)
            )
            if not is_one_time:
                continue

            tz = self._resolve_timezone(alarm.timezone)
            arrival_date = alarm.schedule.specific_date if alarm.schedule else None
            target_arrival_dt = self._calculate_target_arrival_datetime(
                arrival_time=alarm.arrival_time,
                arrival_date=arrival_date,
                tz=tz,
            )

            now_in_tz = datetime.now(tz=tz)
            if target_arrival_dt < now_in_tz:
                alarm.status = AlarmStatus.EXPIRED
                alarm.enabled = False
                expired_count += 1
                publish_alarm_event(
                    AlarmEvent(
                        event_type=AlarmEventType.ALARM_EXPIRED,
                        alarm_id=str(alarm.id),
                        user_id=str(alarm.user_id),
                    )
                )

        if expired_count > 0:
            self.alarm_repo.db.commit()

        return expired_count

    # ------------------------------------------------------------------
    # Next Occurrence Calculation
    # ------------------------------------------------------------------

    def determine_next_occurrence(
        self, alarm: Alarm, from_dt: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Determines the next future arrival datetime for an alarm based on recurrence.
        """
        tz = self._resolve_timezone(alarm.timezone)
        base_now = from_dt or datetime.now(tz=tz)

        sched = alarm.schedule
        if not sched or sched.schedule_type == ScheduleType.ONCE:
            target_date = sched.specific_date if sched and sched.specific_date else base_now.date()
            dt = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                alarm.arrival_time.hour,
                alarm.arrival_time.minute,
                alarm.arrival_time.second,
                tzinfo=tz,
            )
            return dt

        if sched.schedule_type == ScheduleType.DAILY:
            candidate = datetime(
                base_now.year,
                base_now.month,
                base_now.day,
                alarm.arrival_time.hour,
                alarm.arrival_time.minute,
                alarm.arrival_time.second,
                tzinfo=tz,
            )
            if candidate <= base_now:
                candidate += timedelta(days=1)
            return candidate

        if sched.schedule_type == ScheduleType.WEEKDAYS:
            candidate = datetime(
                base_now.year,
                base_now.month,
                base_now.day,
                alarm.arrival_time.hour,
                alarm.arrival_time.minute,
                alarm.arrival_time.second,
                tzinfo=tz,
            )
            if candidate <= base_now:
                candidate += timedelta(days=1)
            while candidate.weekday() >= 5:  # Saturday or Sunday
                candidate += timedelta(days=1)
            return candidate

        return None

    # ------------------------------------------------------------------
    # Internal Calculation & Helper Methods
    # ------------------------------------------------------------------

    async def _calculate_schedule_values(
        self,
        destination: Destination,
        arrival_dt: datetime,
        preparation_time: int,
        safety_buffer: int,
        mode: TransportMode,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
        override_seconds: Optional[int] = None,
    ) -> Tuple[datetime, datetime, datetime, int, int, float]:
        """
        Executes core ETA schedule calculation:
        Planned Arrival = Arrival - Safety Buffer
        Leave = Planned Arrival - Travel
        Wake = Leave - Preparation
        """
        # Resolve coordinates
        dest_lat = destination.latitude
        dest_lng = destination.longitude
        start_lat = origin_lat if origin_lat is not None else dest_lat
        start_lng = origin_lng if origin_lng is not None else dest_lng

        base_secs: int
        traffic_secs: int
        confidence: float
        data_source: str

        if override_seconds is not None:
            base_secs = override_seconds
            traffic_secs = override_seconds
            confidence = CONFIDENCE_GOOGLE_LIVE
            data_source = "override"
        elif start_lat == dest_lat and start_lng == dest_lng:
            # Origin identical to destination (fallback default commute baseline: 35 min)
            base_secs = 2100  # 35 min default
            traffic_secs = 2100
            confidence = CONFIDENCE_HEURISTIC
            data_source = "heuristic"
        else:
            try:
                from app.services.eta_calculation_service import ETACalculationService
                travel_mode = ETACalculationService._map_transport_mode(mode.value)
                route = await self.routing_service.calculate_route(
                    origin_lat=start_lat,
                    origin_lng=start_lng,
                    dest_lat=dest_lat,
                    dest_lng=dest_lng,
                    mode=travel_mode,
                )
                base_secs = route.duration_seconds
                traffic_secs = route.traffic_duration_seconds
                confidence = (
                    CONFIDENCE_GOOGLE_LIVE if route.provider == "google" else CONFIDENCE_MAPBOX_LIVE
                )
                data_source = route.provider
            except Exception as exc:
                logger.warning(f"Routing call failed, applying Haversine fallback: {exc}")
                base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                    start_lat, start_lng, dest_lat, dest_lng, mode
                )
                confidence = CONFIDENCE_HEURISTIC
                data_source = "heuristic"

        # Travel minutes (minimum 1)
        travel_mins = max(1, traffic_secs // 60)
        base_mins = max(1, base_secs // 60)
        traffic_delay_mins = max(0, travel_mins - base_mins)

        # Precise schedule math:
        # Planned Arrival = Arrival - Safety Buffer
        planned_arrival_dt = arrival_dt - timedelta(minutes=safety_buffer)
        # Leave Time = Planned Arrival - Travel Duration
        leave_dt = planned_arrival_dt - timedelta(minutes=travel_mins)
        # Wake Time = Leave Time - Preparation Duration
        wake_dt = leave_dt - timedelta(minutes=preparation_time)

        return (
            wake_dt,
            leave_dt,
            planned_arrival_dt,
            travel_mins,
            traffic_delay_mins,
            confidence,
        )

    def _get_verified_alarm(self, user_id: uuid.UUID, alarm_id: uuid.UUID) -> Alarm:
        """Fetch alarm ensuring user ownership. Throws NotFoundException on cross-user access."""
        alarm = self.alarm_repo.get_by_user_and_id(user_id, alarm_id)
        if not alarm:
            # Check if alarm exists under a different user for security audit log
            raw_alarm = self.alarm_repo.get(alarm_id)
            if raw_alarm and raw_alarm.user_id != user_id:
                logger.warning(
                    f"Cross-user IDOR access attempt detected: User {user_id} requested Alarm {alarm_id} owned by {raw_alarm.user_id}"
                )
                raise NotFoundException("Alarm", alarm_id)
            raise NotFoundException("Alarm", alarm_id)
        return alarm

    def _validate_state_transition(
        self, current_status: AlarmStatus, target_status: AlarmStatus
    ) -> None:
        """Validates that a requested state transition is allowed."""
        if current_status == target_status:
            return

        valid_targets = VALID_STATE_TRANSITIONS.get(current_status, set())
        if target_status not in valid_targets:
            logger.warning(
                f"Invalid alarm state transition requested: {current_status.value} -> {target_status.value}"
            )
            raise ValidationException(
                f"Invalid alarm state transition from '{current_status.value}' to '{target_status.value}'."
            )

    @staticmethod
    def _resolve_timezone(tz_name: Optional[str]) -> ZoneInfo:
        """Safely parses IANA timezone string, falling back to Asia/Kolkata."""
        if not tz_name:
            return ZoneInfo("Asia/Kolkata")
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            return ZoneInfo("Asia/Kolkata")

    @classmethod
    def _calculate_target_arrival_datetime(
        cls,
        arrival_time: time,
        arrival_date: Optional[date] = None,
        tz: Optional[ZoneInfo] = None,
    ) -> datetime:
        """
        Builds a timezone-aware datetime representing the target arrival moment.
        If no specific date is provided, defaults to today. If arrival time has
        passed today by > 1 hour, rolls over to tomorrow for recurring/daily alarms.
        """
        zone = tz or ZoneInfo("Asia/Kolkata")
        now_in_tz = datetime.now(tz=zone)

        if arrival_date:
            return datetime(
                year=arrival_date.year,
                month=arrival_date.month,
                day=arrival_date.day,
                hour=arrival_time.hour,
                minute=arrival_time.minute,
                second=arrival_time.second,
                tzinfo=zone,
            )

        candidate = datetime(
            year=now_in_tz.year,
            month=now_in_tz.month,
            day=now_in_tz.day,
            hour=arrival_time.hour,
            minute=arrival_time.minute,
            second=arrival_time.second,
            tzinfo=zone,
        )

        # For one-time alarms without explicit date, roll over to tomorrow if earlier than now
        if candidate <= now_in_tz - timedelta(minutes=15):
            candidate += timedelta(days=1)

        return candidate

    @staticmethod
    def _acquire_idempotency_lock(
        user_id: uuid.UUID, data: AlarmCreate, idempotency_key: Optional[str]
    ) -> None:
        """
        Prevents duplicate alarm creation if the user double-clicks or multiple identical
        requests are fired within the idempotency/debounce window.
        """
        key_content = (
            idempotency_key
            or f"{user_id}:{data.title}:{data.destination_id}:{data.arrival_time}:{data.preparation_time}:{data.safety_buffer}"
        )
        lock_key = f"ada:idempotency:alarm:{hashlib.sha256(key_content.encode()).hexdigest()}"
        ttl_seconds = 60.0 if idempotency_key else 15.0

        try:
            redis_client = get_redis_client()
            acquired = redis_client.set(lock_key, "1", nx=True, ex=int(ttl_seconds))
            if not acquired:
                logger.warning(f"Duplicate alarm creation prevented by Redis lock: {lock_key}")
                raise ConflictException("A duplicate alarm creation request is already being processed.")
        except ConflictException:
            raise
        except Exception:
            # Fall back to in-memory debounce tracking
            now_ts = datetime.now(timezone.utc).timestamp()
            last_ts = _in_memory_locks.get(lock_key)
            if last_ts and (now_ts - last_ts < ttl_seconds):
                logger.warning(f"Duplicate alarm creation prevented by memory lock: {lock_key}")
                raise ConflictException("A duplicate alarm creation request is already being processed.")
            _in_memory_locks[lock_key] = now_ts
