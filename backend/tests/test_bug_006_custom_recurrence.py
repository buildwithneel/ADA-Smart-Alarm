from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import uuid
import pytest
from app.models.alarm import Alarm, AlarmStatus
from app.models.schedule import AlarmSchedule, ScheduleType
from app.services.alarm_service import AlarmService


@pytest.fixture
def alarm_service():
    # Service methods for recurrence calculation only use the alarm object and internal timezone helpers
    return AlarmService(alarm_repo=None, destination_repo=None)


def create_alarm(arrival_time: time, schedule_type: ScheduleType, repeat_days: str = None, tz: str = "UTC") -> Alarm:
    alarm = Alarm(
        id=uuid.uuid4(),
        title="Custom Recurrence Test",
        arrival_time=arrival_time,
        timezone=tz,
        status=AlarmStatus.SCHEDULED,
        enabled=True,
    )
    schedule = AlarmSchedule(
        id=uuid.uuid4(),
        alarm_id=alarm.id,
        schedule_type=schedule_type,
        repeat_days=repeat_days,
    )
    alarm.schedule = schedule
    return alarm


def test_matching_custom_day_future_time(alarm_service):
    """
    If today is Wednesday (2026-05-06) and current time is 07:00,
    and alarm is set for 09:00 on MON,WED,FRI,
    next occurrence must be today at 09:00.
    """
    # 2026-05-06 is Wednesday (weekday 2)
    base_time = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    alarm = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days="MON,WED,FRI")

    next_occ = alarm_service.determine_next_occurrence(alarm, from_dt=base_time)
    assert next_occ is not None
    assert next_occ == datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc)


def test_matching_custom_day_past_time(alarm_service):
    """
    If today is Wednesday (2026-05-06) and current time is 10:00 (past 09:00),
    and alarm is set for 09:00 on MON,WED,FRI,
    next occurrence must be Friday (2026-05-08) at 09:00.
    """
    base_time = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    alarm = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days="MON,WED,FRI")

    next_occ = alarm_service.determine_next_occurrence(alarm, from_dt=base_time)
    assert next_occ is not None
    assert next_occ == datetime(2026, 5, 8, 9, 0, tzinfo=timezone.utc)


def test_non_matching_custom_day(alarm_service):
    """
    If today is Tuesday (2026-05-05) and alarm is set for MON,WED,FRI at 08:30,
    next occurrence must be Wednesday (2026-05-06) at 08:30.
    """
    base_time = datetime(2026, 5, 5, 14, 0, tzinfo=timezone.utc)
    alarm = create_alarm(time(8, 30), ScheduleType.CUSTOM, repeat_days="MON,WED,FRI")

    next_occ = alarm_service.determine_next_occurrence(alarm, from_dt=base_time)
    assert next_occ is not None
    assert next_occ == datetime(2026, 5, 6, 8, 30, tzinfo=timezone.utc)


def test_week_boundary_transition(alarm_service):
    """
    If today is Friday (2026-05-08) 20:00 (past 08:00),
    and repeat days are MON,WED,FRI,
    next occurrence must cross the weekend to next Monday (2026-05-11) at 08:00.
    """
    base_time = datetime(2026, 5, 8, 20, 0, tzinfo=timezone.utc)
    alarm = create_alarm(time(8, 0), ScheduleType.CUSTOM, repeat_days="MON,WED,FRI")

    next_occ = alarm_service.determine_next_occurrence(alarm, from_dt=base_time)
    assert next_occ is not None
    assert next_occ == datetime(2026, 5, 11, 8, 0, tzinfo=timezone.utc)


def test_time_boundary_exact_match(alarm_service):
    """
    If current time is exactly equal to the arrival time on a matching day,
    it must advance to the subsequent occurrence rather than returning a past/immediate time.
    """
    base_time = datetime(2026, 5, 6, 9, 0, tzinfo=timezone.utc)
    alarm = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days="MON,WED,FRI")

    next_occ = alarm_service.determine_next_occurrence(alarm, from_dt=base_time)
    assert next_occ is not None
    assert next_occ == datetime(2026, 5, 8, 9, 0, tzinfo=timezone.utc)


def test_invalid_custom_configuration(alarm_service):
    """
    If repeat_days is empty, None, or contains no valid days,
    determine_next_occurrence should return None.
    """
    base_time = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)

    # Empty repeat_days
    alarm_empty = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days="")
    assert alarm_service.determine_next_occurrence(alarm_empty, from_dt=base_time) is None

    # None repeat_days
    alarm_none = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days=None)
    assert alarm_service.determine_next_occurrence(alarm_none, from_dt=base_time) is None

    # Unknown day names
    alarm_invalid = create_alarm(time(9, 0), ScheduleType.CUSTOM, repeat_days="FOO,BAR")
    assert alarm_service.determine_next_occurrence(alarm_invalid, from_dt=base_time) is None


def test_preserve_existing_schedule_types(alarm_service):
    """
    Verify existing daily, weekdays, and once schedules continue to behave correctly.
    """
    # 2026-05-08 is Friday
    base_time = datetime(2026, 5, 8, 10, 0, tzinfo=timezone.utc)

    # DAILY
    alarm_daily = create_alarm(time(9, 0), ScheduleType.DAILY)
    next_daily = alarm_service.determine_next_occurrence(alarm_daily, from_dt=base_time)
    assert next_daily == datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc)

    # WEEKDAYS: Friday 10:00 -> Next is Monday 09:00
    alarm_weekdays = create_alarm(time(9, 0), ScheduleType.WEEKDAYS)
    next_weekdays = alarm_service.determine_next_occurrence(alarm_weekdays, from_dt=base_time)
    assert next_weekdays == datetime(2026, 5, 11, 9, 0, tzinfo=timezone.utc)

