from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.errors import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.events import AlarmEvent, AlarmEventType, publish_alarm_event
from app.core.redis import get_redis_client
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.schedule import ScheduleType
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.services.eta_engine import ETACalculationEngine
from app.services.routing_service import RoutingService

logger = logging.getLogger("ada.services.recalculation")

# In-memory distributed lock fallback when Redis is unavailable (e.g. testing)
_in_memory_recalc_locks: Dict[str, float] = {}


@dataclass
class RecalculationResult:
    alarm_id: uuid.UUID
    schedule_changed: bool
    status: str  # "updated", "unchanged", "skipped", "urgent_update", "stale_rejected", "provider_error"
    schedule_version: int
    change_reason: Optional[str] = None
    previous_wake_time: Optional[datetime] = None
    new_wake_time: Optional[datetime] = None
    previous_leave_time: Optional[datetime] = None
    new_leave_time: Optional[datetime] = None
    previous_travel_minutes: Optional[int] = None
    new_travel_minutes: Optional[int] = None
    route_freshness: str = "fresh"
    error_message: Optional[str] = None


class AlarmRecalculationService:
    """
    Step 8 Domain Engine: Real-Time Traffic & Dynamic ETA Recalculation.

    Coordinates:
    1. Upcoming alarm eligibility and refresh windows (query efficiency).
    2. Real-time traffic-aware route retrieval via RoutingService.
    3. Significance thresholds (ETA_CHANGE_THRESHOLD_SECONDS) to prevent schedule churn.
    4. Past wake time / urgent change detection (impossible schedule protection).
    5. Optimistic concurrency & schedule versioning (prevents stale writes).
    6. Distributed locking via Redis (prevents concurrent worker collisions).
    7. Lightweight audit logging via AlarmScheduleChange.
    8. Domain events for downstream notification delivery (Step 9).
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
    # Single Alarm Dynamic Recalculation
    # ------------------------------------------------------------------

    async def recalculate_alarm(
        self,
        alarm_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        expected_version: Optional[int] = None,
        force: bool = False,
        current_user_lat: Optional[float] = None,
        current_user_lng: Optional[float] = None,
        override_traffic_seconds: Optional[int] = None,
        current_time_override: Optional[datetime] = None,
        weather_buffer_minutes: Optional[int] = None,
        schedule_reason_override: Optional[str] = None,
    ) -> RecalculationResult:
        """
        Recalculates an alarm's schedule against live traffic conditions.
        Protects against:
        - Stale worker overwrites (expected_version check)
        - Concurrent execution (Redis lock)
        - Schedule churn (significance threshold)
        - Impossible past wake times (URGENT_SCHEDULE_CHANGE)
        """
        # 1. Acquire distributed lock for this specific alarm
        lock_acquired = self._acquire_recalculation_lock(alarm_id)
        if not lock_acquired:
            logger.warning(f"Recalculation skipped for alarm {alarm_id}: lock already held")
            return RecalculationResult(
                alarm_id=alarm_id,
                schedule_changed=False,
                status="skipped",
                schedule_version=0,
                change_reason="LOCK_CONFLICT",
            )

        try:
            alarm = self.alarm_repo.get(alarm_id)
            if not alarm:
                logger.warning(f"Recalculation failed: Alarm {alarm_id} not found")
                return RecalculationResult(
                    alarm_id=alarm_id,
                    schedule_changed=False,
                    status="not_found",
                    schedule_version=0,
                )

            # Enforce authorization if user_id is provided
            if user_id is not None and alarm.user_id != user_id:
                logger.warning(
                    f"Recalculation authorization failed: user {user_id} does not own alarm {alarm_id}"
                )
                raise ForbiddenException("You do not have permission to access or refresh this alarm.")

            # 2. Skip disabled, expired, completed, or cancelled alarms
            if not alarm.enabled or alarm.status in {
                AlarmStatus.DISABLED,
                AlarmStatus.EXPIRED,
                AlarmStatus.COMPLETED,
                AlarmStatus.CANCELLED,
            }:
                logger.info(f"Skipping recalculation for alarm {alarm_id}: status={alarm.status.value}")
                return RecalculationResult(
                    alarm_id=alarm_id,
                    schedule_changed=False,
                    status="skipped",
                    schedule_version=alarm.schedule_version,
                    change_reason="INACTIVE_STATUS",
                )

            # 3. Optimistic Concurrency / Stale Write Check (Section 10 & 11)
            if expected_version is not None and alarm.schedule_version != expected_version:
                logger.warning(
                    f"Stale update rejected for alarm {alarm_id}: "
                    f"expected version {expected_version}, but DB version is {alarm.schedule_version}"
                )
                return RecalculationResult(
                    alarm_id=alarm_id,
                    schedule_changed=False,
                    status="stale_rejected",
                    schedule_version=alarm.schedule_version,
                    change_reason="SCHEDULE_VERSION_MISMATCH",
                )

            # Resolve timezone and current reference time
            tz = self._resolve_timezone(alarm.timezone)
            now = current_time_override or datetime.now(tz=tz)

            # 4. Check Refresh Frequency / Debounce (unless forced)
            if not force and alarm.last_route_refresh_at:
                last_refresh_aware = self._ensure_tz(alarm.last_route_refresh_at, tz)
                seconds_since_last_refresh = (now - last_refresh_aware).total_seconds()
                if seconds_since_last_refresh < settings.ROUTE_CACHE_TTL_SECONDS:
                    logger.debug(
                        f"Skipping recalculation for alarm {alarm_id}: "
                        f"refreshed {seconds_since_last_refresh:.1f}s ago (< {settings.ROUTE_CACHE_TTL_SECONDS}s)"
                    )
                    return RecalculationResult(
                        alarm_id=alarm_id,
                        schedule_changed=False,
                        status="skipped",
                        schedule_version=alarm.schedule_version,
                        change_reason="RECENTLY_REFRESHED",
                    )

            # 5. Resolve target arrival datetime
            arrival_date = alarm.schedule.specific_date if alarm.schedule else None
            target_arrival_dt = self._calculate_target_arrival_datetime(
                arrival_time=alarm.arrival_time,
                arrival_date=arrival_date,
                tz=tz,
                now_ref=now,
            )

            # 6. Retrieve Live Route Data
            dest = alarm.destination
            start_lat = current_user_lat if current_user_lat is not None else alarm.origin_lat
            start_lng = current_user_lng if current_user_lng is not None else alarm.origin_lng
            if start_lat is None or start_lng is None:
                start_lat = dest.latitude
                start_lng = dest.longitude

            route_fetch_success = False
            base_secs: int = 2100  # Default 35m baseline
            traffic_secs: int = 2100
            provider_name = "heuristic"
            freshness_state = "fresh"

            if override_traffic_seconds is not None:
                traffic_secs = override_traffic_seconds
                base_secs = override_traffic_seconds
                provider_name = "override"
                route_fetch_success = True
            elif start_lat == dest.latitude and start_lng == dest.longitude:
                # Same coordinate baseline
                if alarm.current_travel_minutes:
                    base_secs = alarm.current_travel_minutes * 60
                    traffic_secs = alarm.current_travel_minutes * 60
                route_fetch_success = True
            else:
                try:
                    from app.services.eta_calculation_service import ETACalculationService
                    travel_mode = ETACalculationService._map_transport_mode(alarm.transportation_mode.value)
                    route = await self.routing_service.calculate_route(
                        origin_lat=start_lat,
                        origin_lng=start_lng,
                        dest_lat=dest.latitude,
                        dest_lng=dest.longitude,
                        mode=travel_mode,
                    )
                    base_secs = route.duration_seconds
                    traffic_secs = route.traffic_duration_seconds
                    provider_name = route.provider
                    route_fetch_success = True
                except Exception as exc:
                    logger.warning(
                        f"Live route calculation failed for alarm {alarm_id}: {exc}. Applying resilient fallback."
                    )
                    if alarm.calculated_wake_time is not None:
                        # Retain existing schedule safely; mark route freshness as stale
                        alarm.route_freshness_state = "stale"
                        self.alarm_repo.db.commit()
                        return RecalculationResult(
                            alarm_id=alarm_id,
                            schedule_changed=False,
                            status="provider_error",
                            schedule_version=alarm.schedule_version,
                            route_freshness="stale",
                            error_message=str(exc),
                        )
                    else:
                        base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                            start_lat, start_lng, dest.latitude, dest.longitude, alarm.transportation_mode
                        )
                        provider_name = "heuristic"
                        freshness_state = "fallback"

            # 7. Compute New Schedule Values
            new_travel_mins = max(1, traffic_secs // 60)
            base_travel_mins = max(1, base_secs // 60)
            traffic_delay_mins = max(0, new_travel_mins - base_travel_mins)

            # Apply explicit weather buffer if provided or previously configured
            if weather_buffer_minutes is not None:
                alarm.weather_buffer_minutes = weather_buffer_minutes

            active_weather_buffer = alarm.weather_buffer_minutes or 0
            total_buffer_mins = alarm.safety_buffer + active_weather_buffer

            # Planned Arrival = Arrival - (Safety Buffer + Weather Buffer)
            new_planned_arrival = target_arrival_dt - timedelta(minutes=total_buffer_mins)
            # Leave Time = Planned Arrival - Travel Duration
            new_leave = new_planned_arrival - timedelta(minutes=new_travel_mins)
            # Wake Time = Leave Time - Preparation Duration
            new_wake = new_leave - timedelta(minutes=alarm.preparation_time)

            old_wake = self._ensure_tz(alarm.calculated_wake_time, tz)
            old_leave = self._ensure_tz(alarm.calculated_leave_time, tz)
            old_planned_arrival = self._ensure_tz(alarm.planned_arrival_time, tz)
            old_travel_mins = alarm.current_travel_minutes or new_travel_mins

            # 8. Check Past Wake Time / Urgent Schedule Change (Section 9 & 36)
            is_urgent_past_wake = False
            if new_wake <= now:
                # Impossible schedule protection: new wake time has already passed!
                is_urgent_past_wake = True
                logger.warning(
                    f"Urgent recalculation on alarm {alarm_id}: "
                    f"New wake time {new_wake.isoformat()} is in the past (now: {now.isoformat()}). "
                    f"Flagging URGENT_SCHEDULE_CHANGE."
                )

            # 9. Meaningful Change Detection (Section 7 & 8)
            wake_delta_secs = abs((new_wake - old_wake).total_seconds()) if old_wake else 999999
            leave_delta_secs = abs((new_leave - old_leave).total_seconds()) if old_leave else 999999
            travel_delta_mins = new_travel_mins - old_travel_mins

            threshold_secs = settings.ETA_CHANGE_THRESHOLD_SECONDS

            is_meaningful_change = (
                is_urgent_past_wake
                or wake_delta_secs >= threshold_secs
                or leave_delta_secs >= threshold_secs
                or abs(travel_delta_mins) > 0
                or weather_buffer_minutes is not None
                or schedule_reason_override is not None
                or force
            )

            # If difference is below threshold and not urgent, avoid schedule churn
            if not is_meaningful_change:
                logger.debug(
                    f"Alarm {alarm_id} route refreshed but schedule change insignificant "
                    f"(wake_delta={wake_delta_secs:.0f}s < {threshold_secs}s). Updating freshness timestamp only."
                )
                alarm.last_route_refresh_at = now
                alarm.route_freshness_state = freshness_state
                self.alarm_repo.db.commit()

                return RecalculationResult(
                    alarm_id=alarm_id,
                    schedule_changed=False,
                    status="unchanged",
                    schedule_version=alarm.schedule_version,
                    previous_wake_time=old_wake,
                    new_wake_time=new_wake,
                    previous_leave_time=old_leave,
                    new_leave_time=new_leave,
                    previous_travel_minutes=old_travel_mins,
                    new_travel_minutes=new_travel_mins,
                    route_freshness=freshness_state,
                )

            # 10. Determine Schedule Change Reason
            if schedule_reason_override:
                change_reason = schedule_reason_override
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake
            elif is_urgent_past_wake:
                change_reason = "URGENT_SCHEDULE_CHANGE"
                status_to_set = AlarmStatus.URGENT_SCHEDULE_CHANGE
                # Cap wake time to now so user is notified immediately
                effective_wake = now
            elif weather_buffer_minutes is not None and weather_buffer_minutes > 0:
                change_reason = "WEATHER_BUFFER_APPLIED"
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake
            elif travel_delta_mins > 0:
                change_reason = "TRAFFIC_INCREASE"
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake
            elif travel_delta_mins < 0:
                change_reason = "TRAFFIC_DECREASE"
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake
            elif old_wake and new_wake != old_wake:
                change_reason = "ROUTE_CHANGED"
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake
            else:
                change_reason = "ROUTE_REFRESHED"
                status_to_set = AlarmStatus.SCHEDULED
                effective_wake = new_wake

            # 11. Atomic Persistence: Increment Version & Audit History
            new_version = alarm.schedule_version + 1
            alarm.schedule_version = new_version
            alarm.status = status_to_set
            alarm.calculated_wake_time = effective_wake
            alarm.calculated_leave_time = new_leave
            alarm.planned_arrival_time = new_planned_arrival
            alarm.current_travel_minutes = new_travel_mins
            alarm.traffic_delay_minutes = traffic_delay_mins
            alarm.last_route_refresh_at = now
            alarm.last_schedule_change_at = now
            alarm.schedule_change_reason = change_reason
            alarm.route_freshness_state = freshness_state
            alarm.last_calculated_at = now
            alarm.last_evaluated_at = now

            # Record lightweight audit history entry
            self.alarm_repo.record_schedule_change(
                alarm_id=alarm.id,
                previous_wake_time=old_wake,
                new_wake_time=effective_wake,
                previous_leave_time=old_leave,
                new_leave_time=new_leave,
                previous_planned_arrival=old_planned_arrival,
                new_planned_arrival=new_planned_arrival,
                previous_travel_minutes=old_travel_mins,
                new_travel_minutes=new_travel_mins,
                reason=change_reason,
                schedule_version=new_version,
            )

            self.alarm_repo.db.commit()
            self.alarm_repo.db.refresh(alarm)

            # 12. Emit Domain Event
            event_type = (
                AlarmEventType.ALARM_URGENT_CHANGE
                if is_urgent_past_wake
                else AlarmEventType.ALARM_RECALCULATED
            )
            publish_alarm_event(
                AlarmEvent(
                    event_type=event_type,
                    alarm_id=str(alarm.id),
                    user_id=str(alarm.user_id),
                    payload={
                        "reason": change_reason,
                        "schedule_version": new_version,
                        "old_wake_time": old_wake.isoformat() if old_wake else None,
                        "new_wake_time": effective_wake.isoformat(),
                        "old_leave_time": old_leave.isoformat() if old_leave else None,
                        "new_leave_time": new_leave.isoformat(),
                        "travel_minutes": new_travel_mins,
                        "traffic_delay_minutes": traffic_delay_mins,
                    },
                )
            )

            logger.info(
                f"Schedule updated for Alarm {alarm.id} (v{new_version}): "
                f"Reason={change_reason} | Wake={effective_wake.strftime('%H:%M')} | "
                f"Leave={new_leave.strftime('%H:%M')} | Travel={new_travel_mins}m"
            )

            return RecalculationResult(
                alarm_id=alarm.id,
                schedule_changed=True,
                status="urgent_update" if is_urgent_past_wake else "updated",
                schedule_version=new_version,
                change_reason=change_reason,
                previous_wake_time=old_wake,
                new_wake_time=effective_wake,
                previous_leave_time=old_leave,
                new_leave_time=new_leave,
                previous_travel_minutes=old_travel_mins,
                new_travel_minutes=new_travel_mins,
                route_freshness=freshness_state,
            )

        finally:
            self._release_recalculation_lock(alarm_id)

    # ------------------------------------------------------------------
    # Batch Periodic Upcoming Alarms Evaluation (Celery Beat Task)
    # ------------------------------------------------------------------

    async def refresh_all_upcoming_alarms(
        self,
        window_seconds: Optional[int] = None,
        limit: Optional[int] = None,
        current_time_override: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Batch evaluation task triggered periodically by Celery Beat.
        Queries only upcoming, active alarms within the configurable time horizon,
        evaluates live traffic, and recalculates where appropriate.
        """
        win_secs = window_seconds or settings.UPCOMING_ALARM_WINDOW_SECONDS
        batch_limit = limit or settings.MAX_PROVIDER_REQUESTS_PER_RUN
        now = current_time_override or datetime.now(tz=timezone.utc)

        eligible_alarms = self.alarm_repo.get_alarms_eligible_for_traffic_refresh(
            now_dt=now,
            window_seconds=win_secs,
            limit=batch_limit,
        )

        logger.info(
            f"Upcoming alarms sweep started: {len(eligible_alarms)} alarms eligible "
            f"(window={win_secs}s, limit={batch_limit})"
        )

        stats = {
            "evaluated": len(eligible_alarms),
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "errors": 0,
        }

        for alarm in eligible_alarms:
            try:
                res = await self.recalculate_alarm(
                    alarm_id=alarm.id,
                    expected_version=alarm.schedule_version,
                    force=False,
                    current_time_override=now,
                )
                if res.status in {"updated", "urgent_update"}:
                    stats["updated"] += 1
                elif res.status == "unchanged":
                    stats["unchanged"] += 1
                elif res.status in {"skipped", "stale_rejected"}:
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1
            except Exception as e:
                logger.error(f"Error recalculating alarm {alarm.id}: {e}", exc_info=True)
                stats["errors"] += 1

        logger.info(f"Upcoming alarms sweep finished: {stats}")
        return stats

    # ------------------------------------------------------------------
    # Distributed Locking & Concurrency Helpers
    # ------------------------------------------------------------------

    def _acquire_recalculation_lock(self, alarm_id: uuid.UUID) -> bool:
        """Acquires a non-blocking Redis distributed lock for an alarm."""
        lock_key = f"ada:recalc:lock:{alarm_id}"
        ttl = settings.RECALCULATION_LOCK_TIMEOUT_SECONDS

        try:
            redis_client = get_redis_client()
            acquired = redis_client.set(lock_key, "1", nx=True, ex=ttl)
            return bool(acquired)
        except Exception:
            # In-memory lock fallback for tests/offline
            now_ts = datetime.now(timezone.utc).timestamp()
            last_ts = _in_memory_recalc_locks.get(lock_key)
            if last_ts and (now_ts - last_ts < ttl):
                return False
            _in_memory_recalc_locks[lock_key] = now_ts
            return True

    def _release_recalculation_lock(self, alarm_id: uuid.UUID) -> None:
        """Releases the Redis distributed lock."""
        lock_key = f"ada:recalc:lock:{alarm_id}"
        try:
            redis_client = get_redis_client()
            redis_client.delete(lock_key)
        except Exception:
            _in_memory_recalc_locks.pop(lock_key, None)

    # ------------------------------------------------------------------
    # Internal Timezone & DateTime Resolvers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_timezone(tz_name: Optional[str]) -> ZoneInfo:
        if not tz_name:
            return ZoneInfo("Asia/Kolkata")
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            return ZoneInfo("Asia/Kolkata")

    @staticmethod
    def _ensure_tz(dt: Optional[datetime], target_tz: ZoneInfo) -> Optional[datetime]:
        """Ensures a datetime has timezone information matching target_tz."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=target_tz)
        return dt.astimezone(target_tz)


    @classmethod
    def _calculate_target_arrival_datetime(
        cls,
        arrival_time: time,
        arrival_date: Optional[date] = None,
        tz: Optional[ZoneInfo] = None,
        now_ref: Optional[datetime] = None,
    ) -> datetime:
        zone = tz or ZoneInfo("Asia/Kolkata")
        now_in_tz = now_ref or datetime.now(tz=zone)

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

        if candidate <= now_in_tz - timedelta(minutes=15):
            candidate += timedelta(days=1)

        return candidate
