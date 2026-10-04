from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from typing import Generator
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.errors import ValidationException
from app.main import app as fastapi_app
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.destination import Destination, DestinationType
from app.models.schedule import ScheduleType
from app.models.user import User
from app.schemas.alarm import AlarmCreate, AlarmUpdate
from app.schemas.location import RouteResult
from app.services.alarm_service import AlarmService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        firebase_uid="other-user-firebase-uid-002",
        email="other@ada-alarm.com",
        name="Other User",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_client(db_session: Session, other_user: User) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    headers = {
        "Authorization": f"Bearer test-token:{other_user.firebase_uid}:{other_user.email}:{other_user.name}"
    }
    with TestClient(fastapi_app, headers=headers) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def charusat_destination(client: TestClient) -> dict:
    payload = {
        "name": "CHARUSAT",
        "type": "college",
        "latitude": 22.5996,
        "longitude": 72.8205,
        "address": "CHARUSAT Campus, Changa, Gujarat 388421",
        "provider": "google",
        "is_favorite": True,
    }
    res = client.post("/api/v1/destinations", json=payload)
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# 1. Deterministic Calculation Test (Section 31 of prompt)
# ---------------------------------------------------------------------------

def test_deterministic_alarm_calculation(client: TestClient, charusat_destination: dict):
    """
    Prompt requirement:
    Required arrival: 09:00
    Travel: 35 minutes (2100 seconds)
    Preparation: 30 minutes
    Safety buffer: 10 minutes

    Expected:
    Planned arrival: 08:50
    Leave: 08:15
    Wake: 07:45
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    payload = {
        "title": "CHARUSAT Morning Arrival",
        "destination_id": dest_id,
        "arrival_time": "09:00:00",
        "arrival_date": tomorrow.isoformat(),
        "preparation_time": 30,
        "safety_buffer": 10,
        "transportation_mode": "driving",
        "override_base_duration_seconds": 2100,  # exactly 35 minutes travel
        "timezone": "Asia/Kolkata",
    }

    res = client.post("/api/v1/alarms", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    # Verify times in local timezone
    wake_dt = datetime.fromisoformat(data["calculated_wake_time"])
    leave_dt = datetime.fromisoformat(data["calculated_leave_time"])
    planned_arrival_dt = datetime.fromisoformat(data["planned_arrival_time"])

    # 1. Planned Arrival must be exactly 08:50 (09:00 - 10 min safety buffer)
    assert planned_arrival_dt.hour == 8
    assert planned_arrival_dt.minute == 50

    # 2. Leave Time must be exactly 08:15 (08:50 - 35 min travel)
    assert leave_dt.hour == 8
    assert leave_dt.minute == 15

    # 3. Wake Time must be exactly 07:45 (08:15 - 30 min preparation)
    assert wake_dt.hour == 7
    assert wake_dt.minute == 45

    assert data["status"] == "scheduled"
    assert data["calculation_version"] == "eta-v1"


# ---------------------------------------------------------------------------
# 2. Validation Tests
# ---------------------------------------------------------------------------

def test_create_alarm_invalid_destination(client: TestClient):
    """Creating an alarm for non-existent destination returns 404."""
    random_id = str(uuid.uuid4())
    payload = {
        "title": "Invalid Destination Alarm",
        "destination_id": random_id,
        "arrival_time": "09:00:00",
        "preparation_time": 30,
        "safety_buffer": 10,
    }
    res = client.post("/api/v1/alarms", json=payload)
    assert res.status_code == 404
    assert res.json()["title"] == "NOT_FOUND"


def test_create_alarm_other_user_destination(
    client: TestClient, other_client: TestClient
):
    """User A cannot create an alarm targeting User B's destination."""
    # User B creates a private destination
    b_dest = other_client.post(
        "/api/v1/destinations",
        json={
            "name": "Secret Office",
            "type": "office",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA",
        },
    ).json()

    # User A attempts to create an alarm using User B's destination ID
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Intruder Alarm",
            "destination_id": b_dest["id"],
            "arrival_time": "10:00:00",
        },
    )
    assert res.status_code in {403, 404}


def test_create_alarm_past_arrival_time(client: TestClient, charusat_destination: dict):
    """A one-time alarm scheduled for a past date/time must be rejected with 422."""
    yesterday = (datetime.now() - timedelta(days=1)).date()
    payload = {
        "title": "Yesterday Alarm",
        "destination_id": charusat_destination["id"],
        "arrival_time": "09:00:00",
        "arrival_date": yesterday.isoformat(),
        "preparation_time": 30,
        "safety_buffer": 10,
    }
    res = client.post("/api/v1/alarms", json=payload)
    assert res.status_code == 422
    assert "past" in res.json()["detail"].lower()


def test_create_alarm_invalid_durations(client: TestClient, charusat_destination: dict):
    """Negative or excessive preparation / buffer durations must be rejected."""
    dest_id = charusat_destination["id"]

    # Negative preparation
    res = client.post(
        "/api/v1/alarms",
        json={
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "preparation_time": -5,
        },
    )
    assert res.status_code == 422

    # Excessive preparation (> 360)
    res = client.post(
        "/api/v1/alarms",
        json={
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "preparation_time": 500,
        },
    )
    assert res.status_code == 422

    # Negative buffer
    res = client.post(
        "/api/v1/alarms",
        json={
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "safety_buffer": -10,
        },
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# 3. Timezone & Boundary Conditions (Midnight & Previous Day)
# ---------------------------------------------------------------------------

def test_midnight_boundary_and_previous_day_wake_time(
    client: TestClient, charusat_destination: dict
):
    """
    Tests arrival just after midnight (e.g. 00:30 AM).
    Travel: 45 min, Safety buffer: 15 min, Preparation: 40 min.
    Total commute budget = 45 + 15 = 60 min. Leave = 23:30 (previous day).
    Wake = 23:30 - 40 min = 22:50 (previous day).
    """
    tomorrow = (datetime.now() + timedelta(days=2)).date()
    payload = {
        "title": "Midnight Flight Arrival",
        "destination_id": charusat_destination["id"],
        "arrival_time": "00:30:00",
        "arrival_date": tomorrow.isoformat(),
        "preparation_time": 40,
        "safety_buffer": 15,
        "override_base_duration_seconds": 2700,  # 45 min
        "timezone": "Asia/Kolkata",
    }
    res = client.post("/api/v1/alarms", json=payload)
    assert res.status_code == 201
    data = res.json()

    wake_dt = datetime.fromisoformat(data["calculated_wake_time"])
    leave_dt = datetime.fromisoformat(data["calculated_leave_time"])
    planned_arrival_dt = datetime.fromisoformat(data["planned_arrival_time"])

    # Planned arrival = 00:30 - 15 min = 00:15
    assert planned_arrival_dt.hour == 0
    assert planned_arrival_dt.minute == 15

    # Leave time = 00:15 - 45 min = 23:30 on previous day
    assert leave_dt.hour == 23
    assert leave_dt.minute == 30
    assert leave_dt.date() == tomorrow - timedelta(days=1)

    # Wake time = 23:30 - 40 min = 22:50 on previous day
    assert wake_dt.hour == 22
    assert wake_dt.minute == 50
    assert wake_dt.date() == tomorrow - timedelta(days=1)


# ---------------------------------------------------------------------------
# 4. Lifecycle Operations: Update, Recalculate, Enable, Disable, Delete
# ---------------------------------------------------------------------------

def test_alarm_update_recalculates_schedule(
    client: TestClient, charusat_destination: dict
):
    """Modifying preparation time or safety buffer triggers automatic recalculation."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_payload = {
        "title": "Lecture",
        "destination_id": charusat_destination["id"],
        "arrival_time": "09:00:00",
        "arrival_date": tomorrow.isoformat(),
        "preparation_time": 30,
        "safety_buffer": 10,
        "override_base_duration_seconds": 1800,  # 30 min
    }
    res = client.post("/api/v1/alarms", json=create_payload)
    assert res.status_code == 201
    alarm_id = res.json()["id"]

    # Initial wake = 08:20 - 30 min = 07:50
    init_wake = datetime.fromisoformat(res.json()["calculated_wake_time"])
    assert init_wake.hour == 7 and init_wake.minute == 50

    # Update preparation time to 50 min
    patch_res = client.patch(
        f"/api/v1/alarms/{alarm_id}",
        json={"preparation_time": 50},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    new_wake = datetime.fromisoformat(updated["calculated_wake_time"])

    # New wake = 08:20 - 50 min = 07:30
    assert new_wake.hour == 7 and new_wake.minute == 30
    assert updated["preparation_time"] == 50


def test_alarm_enable_disable_flow(client: TestClient, charusat_destination: dict):
    """Tests POST /alarms/{id}/disable and POST /alarms/{id}/enable."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Toggle Test",
            "destination_id": charusat_destination["id"],
            "arrival_time": "14:00:00",
            "arrival_date": tomorrow.isoformat(),
        },
    )
    assert create_res.status_code == 201
    alarm_id = create_res.json()["id"]
    assert create_res.json()["status"] == "scheduled"
    assert create_res.json()["enabled"] is True

    # 1. Disable alarm
    dis_res = client.post(f"/api/v1/alarms/{alarm_id}/disable")
    assert dis_res.status_code == 200
    dis_data = dis_res.json()
    assert dis_data["enabled"] is False
    assert dis_data["status"] == "disabled"

    # 2. Enable alarm
    en_res = client.post(f"/api/v1/alarms/{alarm_id}/enable")
    assert en_res.status_code == 200
    en_data = en_res.json()
    assert en_data["enabled"] is True
    assert en_data["status"] == "scheduled"


def test_alarm_duplicate(client: TestClient, charusat_destination: dict):
    """POST /alarms/{id}/duplicate creates a new alarm with new UUID and independent record."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "CHARUSAT — Morning",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
        },
    )
    orig_id = create_res.json()["id"]

    # Duplicate
    dup_res = client.post(f"/api/v1/alarms/{orig_id}/duplicate")
    assert dup_res.status_code == 201
    dup_data = dup_res.json()

    assert dup_data["id"] != orig_id
    assert "Copy" in dup_data["title"]
    assert dup_data["destination_id"] == charusat_destination["id"]
    assert dup_data["preparation_time"] == 30
    assert dup_data["status"] == "scheduled"

    # Verify both alarms exist independently
    list_res = client.get("/api/v1/alarms")
    ids = [a["id"] for a in list_res.json()]
    assert orig_id in ids
    assert dup_data["id"] in ids


def test_alarm_refresh_calculation(client: TestClient, charusat_destination: dict):
    """POST /alarms/{id}/refresh updates last_calculated_at and returns fresh schedule."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Refresh Test",
            "destination_id": charusat_destination["id"],
            "arrival_time": "15:00:00",
            "arrival_date": tomorrow.isoformat(),
        },
    )
    alarm_id = create_res.json()["id"]

    refresh_res = client.post(f"/api/v1/alarms/{alarm_id}/refresh")
    assert refresh_res.status_code == 200
    refreshed = refresh_res.json()
    assert refreshed["last_calculated_at"] is not None
    assert refreshed["status"] == "scheduled"


# ---------------------------------------------------------------------------
# 5. Security & Authorization (IDOR Prevention)
# ---------------------------------------------------------------------------

def test_cross_user_isolation(
    client: TestClient, other_client: TestClient, charusat_destination: dict
):
    """User B cannot read, edit, delete, enable, duplicate, or refresh User A's alarm."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    # User A creates alarm
    a_alarm = client.post(
        "/api/v1/alarms",
        json={
            "title": "User A Private Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
        },
    ).json()
    alarm_id = a_alarm["id"]

    # User B attempts to access User A's alarm
    assert other_client.get(f"/api/v1/alarms/{alarm_id}").status_code in {403, 404}
    assert other_client.patch(f"/api/v1/alarms/{alarm_id}", json={"title": "Hacked"}).status_code in {403, 404}
    assert other_client.post(f"/api/v1/alarms/{alarm_id}/disable").status_code in {403, 404}
    assert other_client.post(f"/api/v1/alarms/{alarm_id}/enable").status_code in {403, 404}
    assert other_client.post(f"/api/v1/alarms/{alarm_id}/duplicate").status_code in {403, 404}
    assert other_client.post(f"/api/v1/alarms/{alarm_id}/refresh").status_code in {403, 404}
    assert other_client.delete(f"/api/v1/alarms/{alarm_id}").status_code in {403, 404}


# ---------------------------------------------------------------------------
# 6. Concurrency / Duplicate Creation Protection
# ---------------------------------------------------------------------------

def test_duplicate_alarm_creation_protection(client: TestClient, charusat_destination: dict):
    """Submitting two identical creation requests within the debounce window triggers 409 Conflict."""
    tomorrow = (datetime.now() + timedelta(days=3)).date()
    payload = {
        "title": "Idempotent Alarm",
        "destination_id": charusat_destination["id"],
        "arrival_time": "16:00:00",
        "arrival_date": tomorrow.isoformat(),
        "preparation_time": 25,
        "safety_buffer": 15,
    }

    # First submission succeeds
    res1 = client.post("/api/v1/alarms", json=payload, headers={"X-Idempotency-Key": "test-idem-key-100"})
    assert res1.status_code == 201

    # Immediate second submission with same key is rejected with 409 Conflict
    res2 = client.post("/api/v1/alarms", json=payload, headers={"X-Idempotency-Key": "test-idem-key-100"})
    assert res2.status_code == 409
    assert res2.json()["title"] == "CONFLICT"


# ---------------------------------------------------------------------------
# 7. List Alarms Filtering & Sorting
# ---------------------------------------------------------------------------

def test_list_alarms_filtering(client: TestClient, charusat_destination: dict):
    """Filters upcoming, enabled, and disabled alarms correctly."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    # Create enabled alarm
    client.post(
        "/api/v1/alarms",
        json={
            "title": "Active Early",
            "destination_id": dest_id,
            "arrival_time": "08:00:00",
            "arrival_date": tomorrow.isoformat(),
            "enabled": True,
        },
    )

    # Create disabled alarm
    client.post(
        "/api/v1/alarms",
        json={
            "title": "Disabled Late",
            "destination_id": dest_id,
            "arrival_time": "12:00:00",
            "arrival_date": tomorrow.isoformat(),
            "enabled": False,
        },
    )

    # Filter enabled
    enabled_res = client.get("/api/v1/alarms?filter=enabled")
    assert enabled_res.status_code == 200
    for a in enabled_res.json():
        assert a["enabled"] is True

    # Filter disabled
    disabled_res = client.get("/api/v1/alarms?filter=disabled")
    assert disabled_res.status_code == 200
    for a in disabled_res.json():
        assert a["enabled"] is False
