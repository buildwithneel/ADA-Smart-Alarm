from datetime import datetime, time, timedelta, timezone
import uuid
import pytest
from app.models.alarm import Alarm, AlarmStatus
from app.models.destination import Destination
from app.models.notification import Notification, NotificationStatus
from app.models.schedule import AlarmSchedule, ScheduleType
from app.models.user import User
from app.worker.tasks import reconcile_missed_alarms
from app.core.database import SessionLocal as TestingSessionLocal


@pytest.fixture
def setup_user_and_dest():
    with TestingSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            firebase_uid=f"test_uid_{uuid.uuid4().hex[:8]}",
            email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        )
        session.add(user)
        session.flush()

        dest = Destination(
            id=uuid.uuid4(),
            user_id=user.id,
            name="Office",
            latitude=12.9716,
            longitude=77.5946,
            address="Bangalore",
        )
        session.add(dest)
        session.commit()
        return user.id, dest.id


def test_reconcile_missed_one_time_alarm(setup_user_and_dest):
    """
    Regression test for BUG-003:
    Past one-time alarm should be transitioned to COMPLETED and disabled.
    """
    user_id, dest_id = setup_user_and_dest
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(hours=2)
    alarm_id = uuid.uuid4()

    with TestingSessionLocal() as session:
        one_time_alarm = Alarm(
            id=alarm_id,
            user_id=user_id,
            destination_id=dest_id,
            title="Dentist",
            arrival_time=time(9, 0),
            planned_arrival_time=past_time,
            status=AlarmStatus.SCHEDULED,
            enabled=True,
        )
        session.add(one_time_alarm)
        session.commit()

    res = reconcile_missed_alarms()
    assert res["status"] == "success"
    assert res["alarms_reconciled"] >= 1

    with TestingSessionLocal() as session:
        alarm = session.get(Alarm, alarm_id)
        assert alarm.status == AlarmStatus.COMPLETED
        assert alarm.enabled is False


def test_reconcile_missed_recurring_alarm(setup_user_and_dest):
    """
    Regression test for BUG-003:
    Past recurring alarm should stay enabled and reset to SCHEDULED with rolled-over arrival.
    """
    user_id, dest_id = setup_user_and_dest
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(hours=1)
    alarm_id = uuid.uuid4()

    with TestingSessionLocal() as session:
        recurring_alarm = Alarm(
            id=alarm_id,
            user_id=user_id,
            destination_id=dest_id,
            title="Daily Standup",
            arrival_time=time(10, 0),
            planned_arrival_time=past_time,
            status=AlarmStatus.ACTIVE,
            enabled=True,
            timezone="UTC",
        )
        schedule = AlarmSchedule(
            id=uuid.uuid4(),
            alarm_id=alarm_id,
            schedule_type=ScheduleType.DAILY,
        )
        session.add(recurring_alarm)
        session.add(schedule)
        session.commit()

    res = reconcile_missed_alarms()
    assert res["status"] == "success"

    with TestingSessionLocal() as session:
        alarm = session.get(Alarm, alarm_id)
        assert alarm.status == AlarmStatus.SCHEDULED
        assert alarm.enabled is True
        planned_dt = alarm.planned_arrival_time
        if planned_dt.tzinfo is None:
            planned_dt = planned_dt.replace(tzinfo=timezone.utc)
        assert planned_dt > past_time


def test_future_alarm_untouched(setup_user_and_dest):
    """
    Regression test for BUG-003:
    Future alarms should not be reconciled or modified.
    """
    user_id, dest_id = setup_user_and_dest
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(hours=5)
    alarm_id = uuid.uuid4()

    with TestingSessionLocal() as session:
        future_alarm = Alarm(
            id=alarm_id,
            user_id=user_id,
            destination_id=dest_id,
            title="Future Meeting",
            arrival_time=time(18, 0),
            planned_arrival_time=future_time,
            status=AlarmStatus.SCHEDULED,
            enabled=True,
        )
        session.add(future_alarm)
        session.commit()

    res = reconcile_missed_alarms()
    assert res["status"] == "success"

    with TestingSessionLocal() as session:
        alarm = session.get(Alarm, alarm_id)
        assert alarm.status == AlarmStatus.SCHEDULED
        assert alarm.enabled is True
