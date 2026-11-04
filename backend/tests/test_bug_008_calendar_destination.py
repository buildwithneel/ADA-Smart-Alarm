import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.core.crypto import encrypt_token
from app.core.errors import ForbiddenException, NotFoundException, ValidationException
from app.models.destination import Destination, DestinationType
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.services.calendar.calendar_service import CalendarService


@pytest.fixture
def calendar_service_deps(db_session, test_user: User):
    cal_repo = CalendarRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)
    pref_repo = PreferenceRepository(db_session)
    service = CalendarService(
        calendar_repo=cal_repo,
        alarm_repo=alarm_repo,
        destination_repo=dest_repo,
        pref_repo=pref_repo,
    )
    return service, cal_repo, dest_repo, test_user


@pytest.mark.asyncio
async def test_create_alarm_from_event_constructs_destination(db_session, calendar_service_deps):
    """
    Regression test for BUG-008:
    Verify create_alarm_from_event creates a Destination entity instance
    without raising TypeError: BaseRepository.create() got unexpected keyword arguments.
    """
    service, cal_repo, dest_repo, user = calendar_service_deps

    conn = cal_repo.create_connection(
        user_id=user.id,
        account_email="student@university.edu",
        encrypted_access_token=encrypt_token("mock-access"),
        encrypted_refresh_token=encrypt_token("mock-refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    event, _ = cal_repo.upsert_event(
        connection_id=conn.id,
        user_id=user.id,
        external_event_id=f"evt_geo_{uuid.uuid4().hex[:6]}",
        title="Campus Hackathon",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=3),
        timezone_str="UTC",
        location="Seminar Hall A, Building 3",
        resolved_latitude=12.9716,
        resolved_longitude=77.5946,
    )

    # Call create_alarm_from_event with destination_id=None
    created_alarm = await service.create_alarm_from_event(
        event_id=event.id,
        user_id=user.id,
        destination_id=None,
    )

    assert created_alarm is not None
    assert created_alarm.destination_id is not None

    # Verify created Destination entity
    dest = dest_repo.get(created_alarm.destination_id)
    assert dest is not None
    assert dest.user_id == user.id
    assert dest.latitude == 12.9716
    assert dest.longitude == 77.5946
    assert dest.address == "Seminar Hall A, Building 3"
    assert dest.type == DestinationType.CUSTOM
    assert dest.provider == "calendar"


@pytest.mark.asyncio
async def test_create_alarm_from_event_missing_coordinates_raises_validation_error(db_session, calendar_service_deps):
    """
    Verify ValidationException is raised when event has no resolved coordinates and no destination_id is given.
    """
    service, cal_repo, dest_repo, user = calendar_service_deps

    conn = cal_repo.create_connection(
        user_id=user.id,
        account_email="student@university.edu",
        encrypted_access_token=encrypt_token("mock-access"),
        encrypted_refresh_token=encrypt_token("mock-refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    event, _ = cal_repo.upsert_event(
        connection_id=conn.id,
        user_id=user.id,
        external_event_id=f"evt_no_geo_{uuid.uuid4().hex[:6]}",
        title="Virtual Meeting",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        timezone_str="UTC",
        location=None,
        resolved_latitude=None,
        resolved_longitude=None,
    )

    with pytest.raises(ValidationException):
        await service.create_alarm_from_event(
            event_id=event.id,
            user_id=user.id,
            destination_id=None,
        )


@pytest.mark.asyncio
async def test_create_alarm_from_event_non_existent_event(calendar_service_deps):
    """
    Verify NotFoundException is raised when event does not exist.
    """
    service, _, _, user = calendar_service_deps
    with pytest.raises(NotFoundException):
        await service.create_alarm_from_event(
            event_id=uuid.uuid4(),
            user_id=user.id,
            destination_id=None,
        )


@pytest.mark.asyncio
async def test_create_alarm_from_event_forbidden_user(db_session, calendar_service_deps):
    """
    Verify ForbiddenException is raised when event belongs to another user.
    """
    service, cal_repo, _, user = calendar_service_deps

    other_user = User(
        id=uuid.uuid4(),
        firebase_uid=f"other_{uuid.uuid4().hex[:8]}",
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(other_user)
    db_session.commit()

    conn = cal_repo.create_connection(
        user_id=other_user.id,
        account_email="other@example.com",
        encrypted_access_token=encrypt_token("mock-access"),
        encrypted_refresh_token=encrypt_token("mock-refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    event, _ = cal_repo.upsert_event(
        connection_id=conn.id,
        user_id=other_user.id,
        external_event_id=f"evt_other_{uuid.uuid4().hex[:6]}",
        title="Private Event",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        timezone_str="UTC",
    )

    with pytest.raises(ForbiddenException):
        await service.create_alarm_from_event(
            event_id=event.id,
            user_id=user.id,
            destination_id=None,
        )
