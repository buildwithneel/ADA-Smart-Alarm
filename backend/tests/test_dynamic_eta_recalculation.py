from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Generator
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.core.errors import ForbiddenException
from app.main import app as fastapi_app
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.destination import Destination
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.schemas.location import RouteResult
from app.services.alarm_recalculation_service import AlarmRecalculationService
from app.worker.tasks import refresh_alarm_eta, refresh_upcoming_alarms


@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        firebase_uid="other-user-firebase-uid-step8",
        email="other_step8@ada-alarm.com",
        name="Other Step8 User",
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
        "name": "CHARUSAT Tech Campus",
        "type": "college",
        "latitude": 22.5996,
        "longitude": 72.8205,
        "address": "CHARUSAT, Changa, Gujarat",
        "provider": "google",
        "is_favorite": True,
    }
    res = client.post("/api/v1/destinations", json=payload)
    assert res.status_code == 201
    return res.json()


# ===========================================================================
# 1. Deterministic Traffic Recalculation Test (Section 35)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_deterministic_traffic_increase(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Section 35: IMPORTANT DETERMINISTIC TEST
    Initial:
      Required arrival: 09:00
      Travel: 35 min (2100s)
      Preparation: 30 min
      Safety buffer: 10 min
      Wake: 07:45
      Leave: 08:15
    Traffic update:
      Travel: 55 min (3300s)
    New calculation:
      Planned arrival: 08:50 (09:00 - 10 min buffer)
      Leave: 07:55 (08:50 - 55 min travel)
      Wake: 07:25 (07:55 - 30 min prep)
    Expected:
      Meaningful change detected
      Reason: TRAFFIC_INCREASE
      Schedule version: 2
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    # 1. Create initial alarm with 35 min travel
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Deterministic Morning Trip",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,  # 35 min
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 201
    alarm_data = res.json()
    alarm_id = uuid.UUID(alarm_data["id"])

    # Initial assertion
    wake_1 = datetime.fromisoformat(alarm_data["calculated_wake_time"])
    leave_1 = datetime.fromisoformat(alarm_data["calculated_leave_time"])
    planned_arr_1 = datetime.fromisoformat(alarm_data["planned_arrival_time"])
    assert wake_1.hour == 7 and wake_1.minute == 45
    assert leave_1.hour == 8 and leave_1.minute == 15
    assert planned_arr_1.hour == 8 and planned_arr_1.minute == 50
    assert alarm_data["schedule_version"] == 1

    # 2. Simulate traffic surge: travel increases to 55 min (3300s)
    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    result = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        override_traffic_seconds=3300,  # 55 minutes
        force=True,
    )

    assert result.schedule_changed is True
    assert result.change_reason == "TRAFFIC_INCREASE"
    assert result.schedule_version == 2
    assert result.new_travel_minutes == 55

    # Check updated schedule in DB
    updated = alarm_repo.get(alarm_id)
    assert updated.schedule_version == 2
    assert updated.current_travel_minutes == 55
    assert updated.schedule_change_reason == "TRAFFIC_INCREASE"

    tz = ZoneInfo("Asia/Kolkata")
    new_wake = AlarmRecalculationService._ensure_tz(updated.calculated_wake_time, tz)
    new_leave = AlarmRecalculationService._ensure_tz(updated.calculated_leave_time, tz)
    new_arr = AlarmRecalculationService._ensure_tz(updated.planned_arrival_time, tz)

    assert new_wake.hour == 7 and new_wake.minute == 25
    assert new_leave.hour == 7 and new_leave.minute == 55
    assert new_arr.hour == 8 and new_arr.minute == 50

    # Verify audit history
    history = alarm_repo.get_schedule_changes(alarm_id)
    assert len(history) == 1
    assert history[0].reason == "TRAFFIC_INCREASE"
    assert history[0].previous_travel_minutes == 35
    assert history[0].new_travel_minutes == 55
    assert history[0].schedule_version == 2


# ===========================================================================
# 2. Deterministic Traffic Decrease Test
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_deterministic_traffic_decrease(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Traffic decreases: travel drops from 55 min back to 35 min.
    Wake moves later: 07:25 -> 07:45.
    Reason: TRAFFIC_DECREASE.
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Traffic Decrease Test",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 3300,  # 55 min
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 201
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    result = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        override_traffic_seconds=2100,  # 35 min
        force=True,
    )

    assert result.schedule_changed is True
    assert result.change_reason == "TRAFFIC_DECREASE"
    assert result.schedule_version == 2
    assert result.new_travel_minutes == 35


# ===========================================================================
# 3. Insignificant Traffic Fluctuation (Churn Prevention)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_small_fluctuation_below_threshold_ignored(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Section 7 & 8:
    A tiny change below ETA_CHANGE_THRESHOLD_SECONDS (e.g. 60 seconds) must NOT churn schedule.
    Status remains 'unchanged', schedule_version remains 1, no audit record created.
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Threshold Test Alarm",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,  # 35 min
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 201
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    # Re-evaluate with identical travel time (0s delta)
    result = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        override_traffic_seconds=2100,
        force=False,
    )

    assert result.schedule_changed is False
    assert result.status == "unchanged"
    assert result.schedule_version == 1

    # Verify no audit record was added
    changes = alarm_repo.get_schedule_changes(alarm_id)
    assert len(changes) == 0


# ===========================================================================
# 4. Impossible Update / Urgent Past Wake Time (Section 9 & 36)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_impossible_update_past_wake_time(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Section 36: IMPOSSIBLE UPDATE TEST
    Current reference time: 07:40 AM
    New calculated wake: 07:25 AM
    The system must NOT simply update the alarm to a past wake time.
    It must trigger URGENT_SCHEDULE_CHANGE and cap the wake time to now (07:40 AM).
    """
    tz = ZoneInfo("Asia/Kolkata")
    tomorrow = (datetime.now(tz=tz) + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    # Target arrival tomorrow at 09:00 AM
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Urgent Morning Arrival",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,  # 35 min -> Wake 07:45
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 201
    alarm_id = uuid.UUID(res.json()["id"])

    # Simulate now being tomorrow morning at 07:40 AM
    simulated_now = datetime(
        year=tomorrow.year, month=tomorrow.month, day=tomorrow.day,
        hour=7, minute=40, second=0, tzinfo=tz,
    )

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    # Traffic increases travel to 55 min -> Mathematical wake would be 07:25 AM (past!)
    result = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        override_traffic_seconds=3300,  # 55 min
        force=True,
        current_time_override=simulated_now,
    )

    assert result.schedule_changed is True
    assert result.change_reason == "URGENT_SCHEDULE_CHANGE"
    assert result.status == "urgent_update"

    updated = alarm_repo.get(alarm_id)
    assert updated.status == AlarmStatus.URGENT_SCHEDULE_CHANGE
    assert updated.schedule_change_reason == "URGENT_SCHEDULE_CHANGE"
    # Wake time must not be in the past (capped to simulated_now = 07:40)
    wake_aware = AlarmRecalculationService._ensure_tz(updated.calculated_wake_time, tz)
    assert wake_aware.hour == 7 and wake_aware.minute == 40


# ===========================================================================
# 5. Optimistic Concurrency & Stale Write Rejection (Section 10 & 11)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_stale_task_rejected_by_version_mismatch(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Section 11: RACE CONDITION PROTECTION
    Task A expects version 1, but Alarm was already updated to version 2.
    Task A must be rejected with status='stale_rejected'.
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Concurrency Test",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,
            "timezone": "Asia/Kolkata",
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    # First update moves version to 2
    res1 = await recalc_svc.recalculate_alarm(alarm_id=alarm_id, override_traffic_seconds=3000, force=True)
    assert res1.schedule_version == 2

    # Second update from stale worker expecting version 1
    res2 = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        expected_version=1,
        override_traffic_seconds=3600,
        force=True,
    )

    assert res2.status == "stale_rejected"
    assert res2.schedule_changed is False
    assert res2.schedule_version == 2


# ===========================================================================
# 6. Inactive Alarms Skipped
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_disabled_and_expired_alarms_skipped(client: TestClient, charusat_destination: dict, db_session: Session):
    """Disabled or expired alarms must not be recalculated."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Disabled Alarm",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "enabled": False,
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    result = await recalc_svc.recalculate_alarm(alarm_id=alarm_id, force=False)
    assert result.status == "skipped"
    assert result.schedule_changed is False


# ===========================================================================
# 7. Distributed Lock Prevents Concurrent Refresh (Section 26)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_lock_conflict_skips_concurrent_run(client: TestClient, charusat_destination: dict, db_session: Session):
    """If lock is already held, second recalculation is cleanly skipped."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Lock Test Alarm",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo)

    # Manually hold lock
    lock_key = f"ada:recalc:lock:{alarm_id}"
    from app.services.alarm_recalculation_service import _in_memory_recalc_locks
    _in_memory_recalc_locks[lock_key] = 9999999999.0

    try:
        result = await recalc_svc.recalculate_alarm(alarm_id=alarm_id, force=True)
        assert result.status == "skipped"
        assert result.change_reason == "LOCK_CONFLICT"
    finally:
        _in_memory_recalc_locks.pop(lock_key, None)


# ===========================================================================
# 8. Provider Failure Fallback & Stale Mark (Section 24 & 25)
# ===========================================================================

@pytest.mark.asyncio
async def test_step8_provider_failure_preserves_schedule_and_marks_stale(client: TestClient, charusat_destination: dict, db_session: Session):
    """
    Section 24 & 25:
    If routing provider throws error, do NOT destroy valid alarm schedule.
    Retain existing wake time and mark route freshness state as 'unavailable'.
    """
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    dest_id = charusat_destination["id"]

    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Fallback Test Alarm",
            "destination_id": dest_id,
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    mock_routing = AsyncMock()
    mock_routing.calculate_route.side_effect = RuntimeError("Provider 503 Service Unavailable")

    recalc_svc = AlarmRecalculationService(alarm_repo, dest_repo, routing_service=mock_routing)
    result = await recalc_svc.recalculate_alarm(
        alarm_id=alarm_id,
        current_user_lat=23.0225,
        current_user_lng=72.5714,
        force=True,
    )

    assert result.status == "provider_error"
    assert result.schedule_changed is False

    # Alarm wake time is still intact and data marked stale
    alarm = alarm_repo.get(alarm_id)
    assert alarm.calculated_wake_time is not None
    assert alarm.route_freshness_state == "stale"


# ===========================================================================
# 9. Authorization & IDOR Protection (Section 37)
# ===========================================================================

def test_step8_cross_user_refresh_and_history_forbidden(
    client: TestClient, other_client: TestClient, charusat_destination: dict
):
    """User B cannot refresh or view history of User A's alarm."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "User A Private Recalc Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
        },
    )
    assert create_res.status_code == 201
    alarm_id = create_res.json()["id"]

    # User B tries to refresh User A's alarm -> 404/403
    refresh_res = other_client.post(f"/api/v1/alarms/{alarm_id}/refresh")
    assert refresh_res.status_code in {403, 404}

    # User B tries to access history of User A's alarm -> 404/403
    hist_res = other_client.get(f"/api/v1/alarms/{alarm_id}/history")
    assert hist_res.status_code in {403, 404}


# ===========================================================================
# 10. Audit History API (Section 18 & 16)
# ===========================================================================

def test_step8_history_api_returns_audit_trail(client: TestClient, charusat_destination: dict, db_session: Session):
    """GET /api/v1/alarms/{id}/history returns lightweight audit entries."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "History API Test Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,
        },
    )
    alarm_id = create_res.json()["id"]

    # Manual refresh with traffic increase
    alarm_repo = AlarmRepository(db_session)
    alarm_repo.record_schedule_change(
        alarm_id=uuid.UUID(alarm_id),
        previous_wake_time=datetime.now(timezone.utc),
        new_wake_time=datetime.now(timezone.utc) - timedelta(minutes=20),
        previous_leave_time=datetime.now(timezone.utc) + timedelta(minutes=30),
        new_leave_time=datetime.now(timezone.utc) + timedelta(minutes=10),
        previous_planned_arrival=datetime.now(timezone.utc) + timedelta(hours=1),
        new_planned_arrival=datetime.now(timezone.utc) + timedelta(hours=1),
        previous_travel_minutes=35,
        new_travel_minutes=55,
        reason="TRAFFIC_INCREASE",
        schedule_version=2,
    )
    db_session.commit()

    hist_res = client.get(f"/api/v1/alarms/{alarm_id}/history")
    assert hist_res.status_code == 200
    changes = hist_res.json()
    assert len(changes) == 1
    assert changes[0]["reason"] == "TRAFFIC_INCREASE"
    assert changes[0]["previous_travel_minutes"] == 35
    assert changes[0]["new_travel_minutes"] == 55
    assert changes[0]["schedule_version"] == 2


# ===========================================================================
# 11. Celery Background Tasks Execution
# ===========================================================================

def test_step8_celery_tasks(client: TestClient, charusat_destination: dict, db_session: Session):
    """Verifies that Celery worker tasks execute without error."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    create_res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Celery Worker Test Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "transportation_mode": "driving",
            "override_base_duration_seconds": 2100,
        },
    )
    alarm_id = create_res.json()["id"]

    session_factory = sessionmaker(bind=db_session.get_bind())
    with patch("app.worker.tasks.SessionLocal", side_effect=session_factory):
        # 1. Test single alarm task
        single_res = refresh_alarm_eta(alarm_id)
        assert single_res["status"] in {"updated", "unchanged", "skipped"}

        # 2. Test batch upcoming alarms task
        batch_res = refresh_upcoming_alarms()
        assert batch_res["status"] == "success"
        assert "evaluated_count" in batch_res
