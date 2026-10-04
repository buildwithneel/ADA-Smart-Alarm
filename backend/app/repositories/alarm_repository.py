import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.alarm import Alarm, AlarmStatus
from app.models.schedule import AlarmSchedule
from app.models.schedule_change import AlarmScheduleChange
from app.repositories.base import BaseRepository
from app.schemas.alarm import AlarmCreate, AlarmUpdate

ALARM_MODEL_COLUMNS = {
    "title",
    "destination_id",
    "arrival_time",
    "preparation_time",
    "safety_buffer",
    "transportation_mode",
    "enabled",
    "status",
    "timezone",
    "calculation_version",
    "calculated_wake_time",
    "calculated_leave_time",
    "planned_arrival_time",
    "current_travel_minutes",
    "traffic_delay_minutes",
    "last_evaluated_at",
    "last_calculated_at",
    "origin_lat",
    "origin_lng",
    "origin_address",
    "schedule_version",
    "last_route_refresh_at",
    "last_schedule_change_at",
    "schedule_change_reason",
    "route_freshness_state",
    "weather_buffer_minutes",
    "weather_condition_snapshot",
    "calendar_event_id",
}


class AlarmRepository(BaseRepository[Alarm]):
    """Repository handling Alarm entity persistence with schedule relationships."""

    def __init__(self, db: Session):
        super().__init__(Alarm, db)

    def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[AlarmStatus] = None,
        enabled: Optional[bool] = None,
        filter_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Alarm]:
        stmt = (
            select(Alarm)
            .options(
                joinedload(Alarm.destination),
                joinedload(Alarm.schedule),
                selectinload(Alarm.schedule_changes),
            )
            .where(Alarm.user_id == user_id)
        )

        if status is not None:
            stmt = stmt.where(Alarm.status == status)

        if enabled is not None:
            stmt = stmt.where(Alarm.enabled == enabled)

        if filter_type:
            ft = filter_type.lower()
            if ft == "upcoming" or ft == "scheduled":
                stmt = stmt.where(Alarm.status == AlarmStatus.SCHEDULED, Alarm.enabled.is_(True))
            elif ft == "enabled":
                stmt = stmt.where(Alarm.enabled.is_(True))
            elif ft == "disabled":
                stmt = stmt.where(Alarm.enabled.is_(False))
            elif ft == "expired":
                stmt = stmt.where(Alarm.status == AlarmStatus.EXPIRED)

        stmt = stmt.order_by(Alarm.arrival_time.asc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def get_by_user_and_id(
        self, user_id: uuid.UUID, alarm_id: uuid.UUID
    ) -> Optional[Alarm]:
        stmt = (
            select(Alarm)
            .options(
                joinedload(Alarm.destination),
                joinedload(Alarm.schedule),
                selectinload(Alarm.schedule_changes),
            )
            .where(Alarm.user_id == user_id, Alarm.id == alarm_id)
        )
        return self.db.scalars(stmt).unique().first()

    def create_with_schedule(self, user_id: uuid.UUID, obj_in: AlarmCreate) -> Alarm:
        raw_data = obj_in.model_dump(exclude_unset=True)
        # Filter down to valid Alarm DB column attributes
        alarm_data = {k: v for k, v in raw_data.items() if k in ALARM_MODEL_COLUMNS and v is not None}
        
        # Ensure title and default status
        if "title" not in alarm_data:
            alarm_data["title"] = "Smart Alarm"
        if "status" not in alarm_data:
            alarm_data["status"] = AlarmStatus.SCHEDULED if alarm_data.get("enabled", True) else AlarmStatus.DISABLED

        alarm = Alarm(user_id=user_id, **alarm_data)
        self.db.add(alarm)
        self.db.flush()

        if obj_in.schedule:
            sched_data = obj_in.schedule.model_dump(exclude_unset=True)
            schedule = AlarmSchedule(alarm_id=alarm.id, **sched_data)
            self.db.add(schedule)

        self.db.commit()
        return self.get_by_user_and_id(user_id, alarm.id)  # type: ignore

    def update_with_schedule(self, alarm: Alarm, obj_in: AlarmUpdate) -> Alarm:
        raw_data = obj_in.model_dump(exclude={"schedule"}, exclude_unset=True)
        alarm_data = {k: v for k, v in raw_data.items() if k in ALARM_MODEL_COLUMNS}

        for field, value in alarm_data.items():
            setattr(alarm, field, value)

        if obj_in.schedule is not None:
            sched_data = obj_in.schedule.model_dump(exclude_unset=True)
            if alarm.schedule:
                for s_field, s_val in sched_data.items():
                    setattr(alarm.schedule, s_field, s_val)
            else:
                schedule = AlarmSchedule(alarm_id=alarm.id, **sched_data)
                self.db.add(schedule)

        self.db.commit()
        return self.get_by_user_and_id(alarm.user_id, alarm.id)  # type: ignore

    def update_schedule_calculation(
        self,
        alarm: Alarm,
        calculated_wake_time: datetime,
        calculated_leave_time: datetime,
        planned_arrival_time: datetime,
        current_travel_minutes: int,
        traffic_delay_minutes: int,
        calculation_version: str = "eta-v1",
    ) -> Alarm:
        """
        Persist dynamic smart alarm calculations into DB record.
        """
        now = datetime.now(tz=timezone.utc)
        alarm.calculated_wake_time = calculated_wake_time
        alarm.calculated_leave_time = calculated_leave_time
        alarm.planned_arrival_time = planned_arrival_time
        alarm.current_travel_minutes = current_travel_minutes
        alarm.traffic_delay_minutes = traffic_delay_minutes
        alarm.calculation_version = calculation_version
        alarm.last_calculated_at = now
        alarm.last_evaluated_at = now

        self.db.commit()
        return self.get_by_user_and_id(alarm.user_id, alarm.id) or alarm

    def update_eta_fields(
        self,
        alarm: Alarm,
        calculated_wake_time: datetime,
        calculated_leave_time: datetime,
        current_travel_minutes: int,
        traffic_delay_minutes: int,
    ) -> Alarm:
        """Backwards compatible ETA fields updater."""
        alarm.calculated_wake_time = calculated_wake_time
        alarm.calculated_leave_time = calculated_leave_time
        alarm.current_travel_minutes = current_travel_minutes
        alarm.traffic_delay_minutes = traffic_delay_minutes
        alarm.last_evaluated_at = datetime.now(tz=timezone.utc)
        alarm.last_calculated_at = datetime.now(tz=timezone.utc)
        self.db.commit()
        self.db.refresh(alarm)
        return alarm

        stmt = (
            select(Alarm)
            .options(
                joinedload(Alarm.destination),
                joinedload(Alarm.schedule),
            )
            .where(Alarm.enabled.is_(True), Alarm.status == AlarmStatus.SCHEDULED)
            .order_by(Alarm.arrival_time.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_alarms_eligible_for_traffic_refresh(
        self,
        now_dt: datetime,
        window_seconds: int = 14400,
        limit: int = 50,
    ) -> list[Alarm]:
        """
        Database query efficiency:
        Only loads alarms that are:
        - enabled == True
        - status IN [SCHEDULED, ACTIVE, URGENT_SCHEDULE_CHANGE]
        - calculated_leave_time between (now_dt - 15m) and (now_dt + window_seconds)
        - Eagerly loads destination and schedule to avoid N+1 queries.
        - Ordered by calculated_leave_time ASC.
        """
        horizon = now_dt + timedelta(seconds=window_seconds)
        past_grace = now_dt - timedelta(minutes=15)
        stmt = (
            select(Alarm)
            .options(
                joinedload(Alarm.destination),
                joinedload(Alarm.schedule),
                selectinload(Alarm.schedule_changes),
            )
            .where(
                Alarm.enabled.is_(True),
                Alarm.status.in_([
                    AlarmStatus.SCHEDULED,
                    AlarmStatus.ACTIVE,
                    AlarmStatus.URGENT_SCHEDULE_CHANGE,
                ]),
                Alarm.calculated_leave_time.is_not(None),
                Alarm.calculated_leave_time >= past_grace,
                Alarm.calculated_leave_time <= horizon,
            )
            .order_by(Alarm.calculated_leave_time.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).unique().all())

    def record_schedule_change(
        self,
        alarm_id: uuid.UUID,
        previous_wake_time: Optional[datetime],
        new_wake_time: datetime,
        previous_leave_time: Optional[datetime],
        new_leave_time: datetime,
        previous_planned_arrival: Optional[datetime],
        new_planned_arrival: datetime,
        previous_travel_minutes: Optional[int],
        new_travel_minutes: int,
        reason: str,
        schedule_version: int,
    ) -> AlarmScheduleChange:
        """
        Records a meaningful schedule change into the audit history table.
        """
        change = AlarmScheduleChange(
            alarm_id=alarm_id,
            previous_wake_time=previous_wake_time,
            new_wake_time=new_wake_time,
            previous_leave_time=previous_leave_time,
            new_leave_time=new_leave_time,
            previous_planned_arrival=previous_planned_arrival,
            new_planned_arrival=new_planned_arrival,
            previous_travel_minutes=previous_travel_minutes,
            new_travel_minutes=new_travel_minutes,
            reason=reason,
            schedule_version=schedule_version,
        )
        self.db.add(change)
        self.db.commit()
        self.db.refresh(change)
        return change

    def get_schedule_changes(
        self, alarm_id: uuid.UUID, limit: int = 20
    ) -> list[AlarmScheduleChange]:
        """
        Retrieves the audit trail of schedule changes for an alarm.
        """
        stmt = (
            select(AlarmScheduleChange)
            .where(AlarmScheduleChange.alarm_id == alarm_id)
            .order_by(AlarmScheduleChange.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
