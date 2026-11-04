from datetime import datetime, time, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.destination import Destination
from app.models.schedule import AlarmSchedule, ScheduleType
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.preference_repository import PreferenceRepository
from app.services.user_service import UserService


def test_export_user_data_no_alarms(db_session):
    """
    Regression test for BUG-004:
    User with no alarms exports data cleanly.
    """
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"uid_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    db_session.commit()

    service = UserService(UserRepository(db_session), PreferenceRepository(db_session))
    data = service.export_user_data(user.id)
    assert data["user"]["id"] == str(user.id)
    assert data["alarms"] == []


def test_export_user_data_with_multiple_alarms_and_states(db_session):
    """
    Regression test for BUG-004:
    User with multiple alarms across states and recurring schedules exports without AttributeError.
    """
    user = User(
        id=uuid.uuid4(),
        firebase_uid=f"uid_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    db_session.flush()

    dest = Destination(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Airport",
        latitude=13.1986,
        longitude=77.7066,
        address="Kempegowda Airport",
    )
    db_session.add(dest)
    db_session.flush()

    now = datetime.now(timezone.utc)

    # Alarm 1: One-time scheduled
    alarm1 = Alarm(
        id=uuid.uuid4(),
        user_id=user.id,
        destination_id=dest.id,
        title="Flight Alarm",
        arrival_time=time(6, 30),
        planned_arrival_time=now + timedelta(days=1),
        calculated_wake_time=now + timedelta(days=1, hours=-2),
        calculated_leave_time=now + timedelta(days=1, hours=-1),
        transportation_mode=TransportMode.DRIVING,
        status=AlarmStatus.SCHEDULED,
        enabled=True,
    )
    # Alarm 2: Recurring daily
    alarm2 = Alarm(
        id=uuid.uuid4(),
        user_id=user.id,
        destination_id=dest.id,
        title="Work Gym",
        arrival_time=time(8, 0),
        planned_arrival_time=now + timedelta(days=2),
        transportation_mode=TransportMode.TRANSIT,
        status=AlarmStatus.ACTIVE,
        enabled=True,
    )
    schedule2 = AlarmSchedule(
        id=uuid.uuid4(),
        alarm_id=alarm2.id,
        schedule_type=ScheduleType.DAILY,
    )
    # Alarm 3: Completed one-time
    alarm3 = Alarm(
        id=uuid.uuid4(),
        user_id=user.id,
        destination_id=dest.id,
        title="Past Dinner",
        arrival_time=time(20, 0),
        transportation_mode=TransportMode.WALKING,
        status=AlarmStatus.COMPLETED,
        enabled=False,
    )

    db_session.add_all([alarm1, alarm2, schedule2, alarm3])
    db_session.commit()

    service = UserService(UserRepository(db_session), PreferenceRepository(db_session))
    data = service.export_user_data(user.id)

    assert len(data["alarms"]) == 3
    alarms_by_id = {a["id"]: a for a in data["alarms"]}

    # Verify Alarm 1 fields
    a1 = alarms_by_id[str(alarm1.id)]
    assert a1["title"] == "Flight Alarm"
    assert a1["status"] == "scheduled"
    assert a1["is_active"] is True
    assert a1["transport_mode"] == "driving"
    assert a1["target_arrival_time"] is not None

    # Verify Alarm 2 fields
    a2 = alarms_by_id[str(alarm2.id)]
    assert a2["title"] == "Work Gym"
    assert a2["status"] == "active"
    assert a2["is_active"] is True
    assert a2["transport_mode"] == "transit"

    # Verify Alarm 3 fields
    a3 = alarms_by_id[str(alarm3.id)]
    assert a3["title"] == "Past Dinner"
    assert a3["status"] == "completed"
    assert a3["is_active"] is False
    assert a3["transport_mode"] == "walking"


def test_export_user_data_api_endpoint(client: TestClient, test_user: User, db_session):
    """
    Regression test for BUG-004:
    Verify GET /api/v1/users/me/data returns 200 and valid JSON data for authenticated user.
    """
    dest = Destination(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Gym",
        latitude=12.92,
        longitude=77.61,
        address="Koramangala",
    )
    alarm = Alarm(
        id=uuid.uuid4(),
        user_id=test_user.id,
        destination_id=dest.id,
        title="Morning Session",
        arrival_time=time(7, 0),
        transportation_mode=TransportMode.BICYCLING,
        status=AlarmStatus.SCHEDULED,
        enabled=True,
    )
    db_session.add_all([dest, alarm])
    db_session.commit()

    response = client.get("/api/v1/users/me/data")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["user"]["email"] == test_user.email
    assert len(res_data["alarms"]) >= 1
    found = [a for a in res_data["alarms"] if a["id"] == str(alarm.id)][0]
    assert found["transport_mode"] == "bicycling"
    assert found["is_active"] is True
