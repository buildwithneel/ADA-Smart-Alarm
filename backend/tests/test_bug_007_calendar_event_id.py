from datetime import datetime, time, timezone
import uuid
import pytest
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.schemas.alarm import AlarmCreate, AlarmResponse


def make_dummy_alarm(cal_id):
    alarm = Alarm(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        destination_id=uuid.uuid4(),
        title="Calendar Synced Alarm",
        arrival_time=time(9, 30),
        preparation_time=30,
        safety_buffer=15,
        transportation_mode=TransportMode.DRIVING,
        timezone="Asia/Kolkata",
        calculation_version="eta-v1",
        schedule_version=1,
        route_freshness_state="fresh",
        status=AlarmStatus.SCHEDULED,
        enabled=True,
        calendar_event_id=str(cal_id) if cal_id is not None else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return alarm


@pytest.mark.parametrize(
    "event_id,expected_output",
    [
        ("google_event_1234567890abcdef", "google_event_1234567890abcdef"),
        ("c8a7b9efg123_20260401T090000Z@google.com", "c8a7b9efg123_20260401T090000Z@google.com"),
        ("google-evt-101", "google-evt-101"),
        ("event_id.v1#42-instance", "event_id.v1#42-instance"),
        (None, None),
        ("123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174000"),
    ],
)
def test_alarm_response_serialization_with_calendar_ids(event_id, expected_output):
    """
    Regression test for BUG-007:
    AlarmResponse must accept alphanumeric, special-character, UUID, and None calendar event IDs
    without raising pydantic_core.ValidationError.
    """
    alarm = make_dummy_alarm(event_id)
    response = AlarmResponse.model_validate(alarm)
    assert response.calendar_event_id == expected_output

    # Check json serialization
    dumped = response.model_dump()
    assert dumped["calendar_event_id"] == expected_output


def test_alarm_create_with_calendar_id():
    """
    Verify AlarmCreate schema accepts calendar_event_id.
    """
    payload = {
        "title": "Meeting Alarm",
        "destination_id": uuid.uuid4(),
        "arrival_time": "10:00:00",
        "calendar_event_id": "alphanumeric_google_cal_id_999",
    }
    alarm_in = AlarmCreate(**payload)
    assert alarm_in.calendar_event_id == "alphanumeric_google_cal_id_999"
