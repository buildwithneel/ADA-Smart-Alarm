from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.events import AlarmEvent, AlarmEventType
from app.main import app as fastapi_app
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.calendar import CalendarConnection, CalendarEvent
from app.models.destination import Destination
from app.models.preference import UserPreference
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.services.calendar.base import CalendarEventData
from app.services.calendar.calendar_service import CalendarService
from app.services.context.context_service import (
    ContextAction,
    ContextFinding,
    ContextResult,
    ContextService,
    ContextType,
)
from app.services.weather.base import (
    WeatherAlert,
    WeatherAlertSeverity,
    WeatherCondition,
    WeatherData,
    WeatherProvider,
)
from app.services.weather.weather_service import JourneyWeatherSummary, WeatherService
from app.worker.tasks import evaluate_upcoming_weather_context, sync_active_calendars


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        firebase_uid="other-user-step10",
        email="other_step10@ada-alarm.com",
        name="Other Step10 User",
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


class MockDeterministicWeatherProvider(WeatherProvider):
    def __init__(
        self,
        condition: WeatherCondition = WeatherCondition.CLEAR,
        condition_text: str = "Clear sky",
        precipitation_mm: float = 0.0,
        precipitation_prob: int = 0,
        is_severe: bool = False,
        alerts: list = None,
        retrieved_at: datetime = None,
    ):
        self._condition = condition
        self._condition_text = condition_text
        self._precipitation_mm = precipitation_mm
        self._precipitation_prob = precipitation_prob
        self._is_severe = is_severe
        self._alerts = alerts or []
        self._retrieved_at = retrieved_at or datetime.now(timezone.utc)

    @property
    def provider_name(self) -> str:
        return "mock-meteo"

    @property
    def attribution(self) -> str:
        return "Mock Weather Service"

    async def get_forecast(self, latitude: float, longitude: float, target_time: datetime) -> WeatherData:
        return WeatherData(
            latitude=latitude,
            longitude=longitude,
            timestamp=target_time,
            valid_from=target_time - timedelta(minutes=30),
            valid_until=target_time + timedelta(minutes=30),
            temperature_c=24.5,
            precipitation_probability=self._precipitation_prob,
            precipitation_mm=self._precipitation_mm,
            condition=self._condition,
            condition_text=self._condition_text,
            wind_speed_kmh=12.0,
            is_severe=self._is_severe,
            alerts=self._alerts,
            provider=self.provider_name,
            retrieved_at=self._retrieved_at,
            attribution=self.attribution,
        )

    async def get_current_weather(self, latitude: float, longitude: float) -> WeatherData:
        now = datetime.now(timezone.utc)
        return await self.get_forecast(latitude, longitude, now)


# ===========================================================================
# 1. Weather Provider & Journey Relevance Tests (Scenarios 1, 2, 3, 4, 5)
# ===========================================================================

@pytest.mark.asyncio
async def test_valid_current_and_forecast_weather():
    """Section 2: Normalized Weather Model & WeatherService caching."""
    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.RAIN,
        condition_text="Moderate rain",
        precipitation_mm=2.5,
        precipitation_prob=80,
    )
    weather_svc = WeatherService(provider=provider)

    now = datetime.now(timezone.utc)
    weather = await weather_svc.get_forecast(22.5996, 72.8205, now)

    assert weather.condition == WeatherCondition.RAIN
    assert weather.condition_text == "Moderate rain"
    assert weather.precipitation_mm == 2.5
    assert weather.precipitation_probability == 80
    assert weather.provider == "mock-meteo"
    assert weather.temperature_c == 24.5


@pytest.mark.asyncio
async def test_forecast_valid_at_departure_time():
    """Section 4: Weather evaluated against actual journey time window."""
    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.RAIN,
        condition_text="Heavy rain",
        precipitation_mm=4.0,
    )
    weather_svc = WeatherService(provider=provider)

    leave_time = datetime.now(timezone.utc) + timedelta(hours=1)
    arrival_time = leave_time + timedelta(minutes=45)

    summary = await weather_svc.evaluate_journey_weather(
        origin_lat=23.0225,
        origin_lng=72.5714,
        dest_lat=22.5996,
        dest_lng=72.8205,
        leave_time=leave_time,
        arrival_time=arrival_time,
    )

    assert summary.has_precipitation is True
    assert summary.condition == WeatherCondition.RAIN
    assert "Heavy rain expected during journey" in summary.explanation


@pytest.mark.asyncio
async def test_stale_weather_data_handling():
    """Section 4 & 6: Stale weather data must not trigger automatic adjustments."""
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)  # older than 1 hour TTL
    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.RAIN,
        condition_text="Rain",
        precipitation_mm=1.5,
        retrieved_at=old_time,
    )
    weather_svc = WeatherService(provider=provider)

    summary = await weather_svc.evaluate_journey_weather(
        origin_lat=None,
        origin_lng=None,
        dest_lat=22.5996,
        dest_lng=72.8205,
        leave_time=datetime.now(timezone.utc),
        arrival_time=datetime.now(timezone.utc) + timedelta(minutes=40),
    )

    assert summary.is_stale is True
    assert "outdated" in summary.explanation


@pytest.mark.asyncio
async def test_severe_weather_alert_does_not_silently_change_alarm(
    client: TestClient, charusat_destination: dict, db_session: Session
):
    """
    Section 7: Severe weather alert prioritizes warning & official URL.
    Does NOT silently reschedule alarm solely because an alert exists.
    """
    alert = WeatherAlert(
        title="Flash Flood Warning",
        description="Severe flooding reported along central state corridor.",
        severity=WeatherAlertSeverity.EXTREME,
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
        source="State Meteorological Department",
        official_url="https://weather.gov/alerts/123",
    )
    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.THUNDERSTORM,
        condition_text="Severe Thunderstorm",
        is_severe=True,
        alerts=[alert],
    )
    weather_svc = WeatherService(provider=provider)

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Severe Weather Trip",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    context_svc = ContextService(
        alarm_repo=AlarmRepository(db_session),
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=CalendarRepository(db_session),
        weather_service=weather_svc,
    )

    results = await context_svc.evaluate_alarm_context(alarm_id)
    weather_res = next(r for r in results if r.context_type == ContextType.WEATHER)

    assert weather_res.finding == ContextFinding.SEVERE_WEATHER_ALERT
    assert weather_res.recommended_action == ContextAction.WARN_USER
    assert weather_res.recommended_buffer_minutes == 0  # No arbitrary silent multiplier
    assert "Flash Flood Warning" in str(weather_res.metadata)


# ===========================================================================
# 2. Weather Buffer Policies & Step 8 Recalculation (Section 5 & 6)
# ===========================================================================

@pytest.mark.asyncio
async def test_weather_policy_disabled_and_informational(
    client: TestClient, charusat_destination: dict, db_session: Session
):
    """
    Scenario A: User creates a smart alarm. Rain is forecast.
    With default policy (informational_only, buffer disabled):
    UI displays warning, alarm remains unchanged.
    """
    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.RAIN,
        condition_text="Showers",
        precipitation_mm=2.0,
    )
    weather_svc = WeatherService(provider=provider)

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Informational Weather Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "override_base_duration_seconds": 2100,  # 35 min
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])
    initial_wake = res.json()["calculated_wake_time"]

    context_svc = ContextService(
        alarm_repo=AlarmRepository(db_session),
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=CalendarRepository(db_session),
        weather_service=weather_svc,
    )

    results = await context_svc.evaluate_alarm_context(alarm_id)
    weather_res = next(r for r in results if r.context_type == ContextType.WEATHER)

    assert weather_res.finding == ContextFinding.RAIN_DURING_JOURNEY
    assert weather_res.recommended_action == ContextAction.WARN_USER
    assert weather_res.recommended_buffer_minutes == 0

    # Alarm wake time has NOT changed
    alarm_repo = AlarmRepository(db_session)
    alarm = alarm_repo.get(alarm_id)
    def to_utc(dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    init_dt = to_utc(datetime.fromisoformat(initial_wake.replace("Z", "+00:00")))
    wake_dt = to_utc(alarm.calculated_wake_time)
    assert abs((wake_dt - init_dt).total_seconds()) < 2


@pytest.mark.asyncio
async def test_user_confirmed_weather_adjustment(
    client: TestClient, charusat_destination: dict, db_session: Session
):
    """
    User preference has weather_buffer_mode='user_confirmed'.
    ADA recommends adjustment. Alarm schedule changes ONLY after explicit POST call.
    """
    # 1. Update user preferences to user_confirmed
    client.patch(
        "/api/v1/users/me/preferences",
        json={
            "weather_buffer_enabled": True,
            "weather_buffer_mode": "user_confirmed",
            "weather_buffer_minutes": 15,
        },
    )

    provider = MockDeterministicWeatherProvider(
        condition=WeatherCondition.RAIN,
        condition_text="Heavy rain",
        precipitation_mm=3.0,
    )
    weather_svc = WeatherService(provider=provider)

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Confirmed Weather Adjustment Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "override_base_duration_seconds": 2100,  # 35 min
            "timezone": "Asia/Kolkata",
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])
    orig_version = res.json()["schedule_version"]

    context_svc = ContextService(
        alarm_repo=AlarmRepository(db_session),
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=CalendarRepository(db_session),
        weather_service=weather_svc,
    )

    results = await context_svc.evaluate_alarm_context(alarm_id)
    weather_res = next(r for r in results if r.context_type == ContextType.WEATHER)

    assert weather_res.finding == ContextFinding.RAIN_DURING_JOURNEY
    assert weather_res.recommended_action == ContextAction.APPLY_BUFFER
    assert weather_res.recommended_buffer_minutes == 15
    assert weather_res.requires_confirmation is True

    # 2. User confirms by clicking "Apply adjustment"
    apply_res = client.post(
        f"/api/v1/context/alarm/{alarm_id}/apply-weather-buffer",
        json={"buffer_minutes": 15, "expected_version": orig_version},
    )
    assert apply_res.status_code == 200
    updated = apply_res.json()

    assert updated["schedule_version"] == orig_version + 1
    assert updated["weather_buffer_minutes"] == 15
    assert updated["schedule_change_reason"] == "WEATHER_BUFFER_APPLIED"

    # Verify wake time moved earlier by exactly 15 minutes!
    orig_wake = datetime.fromisoformat(res.json()["calculated_wake_time"])
    new_wake = datetime.fromisoformat(updated["calculated_wake_time"])
    assert (orig_wake - new_wake).total_seconds() == 15 * 60


@pytest.mark.asyncio
async def test_maximum_weather_buffer_enforcement(
    client: TestClient, charusat_destination: dict, db_session: Session
):
    """Section 6 & 13: Cap additional buffer at WEATHER_BUFFER_MAX_MINUTES (30 min)."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Max Buffer Test Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
            "override_base_duration_seconds": 2100,
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])

    # Attempt to apply 60 minutes weather buffer (exceeding maximum 30)
    context_svc = ContextService(
        alarm_repo=AlarmRepository(db_session),
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=CalendarRepository(db_session),
    )

    result = await context_svc.apply_weather_buffer(
        alarm_id=alarm_id,
        user_id=uuid.UUID(res.json()["user_id"]),
        buffer_minutes=60,
    )

    alarm_repo = AlarmRepository(db_session)
    alarm = alarm_repo.get(alarm_id)
    assert alarm.weather_buffer_minutes == 30  # Strictly capped at 30 min


# ===========================================================================
# 3. Calendar Integration & OAuth Tests (Sections 9, 10, 11, 12, 13)
# ===========================================================================

def test_token_encryption_and_decryption_at_rest():
    """Section 11 & 24: Sensitive OAuth tokens encrypted at rest."""
    sample_token = "ya29.a0AfH6SMD_secret_google_oauth_token_12345"
    ciphertext = encrypt_token(sample_token)

    assert ciphertext != sample_token
    assert "ya29" not in ciphertext
    assert decrypt_token(ciphertext) == sample_token


def test_calendar_oauth_auth_url_generation(client: TestClient):
    """Section 11: Least-privilege OAuth authorization URL."""
    with patch("app.core.config.settings.GOOGLE_CALENDAR_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        res = client.post("/api/v1/calendar/connections/auth-url")
        assert res.status_code == 200
        data = res.json()
        assert "authorization_url" in data
        assert "calendar.events.readonly" in data["authorization_url"]
        assert "client_id=mock-google-client-id" in data["authorization_url"]


@pytest.mark.asyncio
async def test_calendar_event_synchronization_and_creation(
    client: TestClient, db_session: Session, test_user: User
):
    """
    Section 12: Sync authorized events and create alarm based on calendar event.
    """
    # 1. Create a mock connection with encrypted token
    cal_repo = CalendarRepository(db_session)

    conn = cal_repo.create_connection(
        user_id=test_user.id,
        account_email="student@charusat.edu.in",
        encrypted_access_token=encrypt_token("mock-access-token"),
        encrypted_refresh_token=encrypt_token("mock-refresh-token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # 2. Mock provider returning an event at CHARUSAT
    target_start = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    mock_events = [
        CalendarEventData(
            external_event_id="google-evt-101",
            title="Advanced Algorithms Lecture",
            start_time=target_start,
            end_time=target_start + timedelta(hours=1),
            timezone="Asia/Kolkata",
            location="CHARUSAT Campus, Changa",
            status="confirmed",
        )
    ]

    mock_provider = MagicMock()
    mock_provider.provider_name = "google"
    mock_provider.list_upcoming_events = AsyncMock(return_value=mock_events)

    cal_service = CalendarService(
        calendar_repo=cal_repo,
        alarm_repo=AlarmRepository(db_session),
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        provider=mock_provider,
    )

    # 3. Synchronize
    sync_res = await cal_service.sync_connection_events(conn.id)
    assert sync_res["status"] == "success"
    assert sync_res["created_count"] == 1

    # Verify event stored
    saved_event = cal_repo.get_event_by_external_id(conn.id, "google-evt-101")
    assert saved_event is not None
    assert saved_event.title == "Advanced Algorithms Lecture"

    # 4. Propose Alarm
    proposal = await cal_service.propose_alarm_from_event(saved_event.id, test_user.id)
    assert proposal["event_title"] == "Advanced Algorithms Lecture"
    assert proposal["proposed_arrival_time"] == target_start.strftime("%H:%M:%S")

    # 5. Confirm and Create Alarm
    # Provide destination coordinates for Changa
    dest = Destination(
        user_id=test_user.id,
        name="CHARUSAT Campus",
        type="college",
        latitude=22.5996,
        longitude=72.8205,
        address="CHARUSAT, Changa",
        provider="google",
    )
    db_session.add(dest)
    db_session.commit()
    db_session.refresh(dest)

    created_alarm = await cal_service.create_alarm_from_event(
        event_id=saved_event.id,
        user_id=test_user.id,
        destination_id=dest.id,
        preparation_time=25,
        safety_buffer=10,
    )

    assert created_alarm is not None
    assert created_alarm.calendar_event_id == "google-evt-101"
    assert saved_event.alarm_id == created_alarm.id


@pytest.mark.asyncio
async def test_calendar_event_cancelled_policy(db_session: Session, test_user: User):
    """
    Section 13: If an event is cancelled, do NOT silently delete the alarm.
    Context findings notify user of cancellation.
    """
    cal_repo = CalendarRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)

    dest = Destination(
        user_id=test_user.id,
        name="Test Dest",
        type="college",
        latitude=22.5,
        longitude=72.8,
        address="Test Address",
        provider="google",
    )
    db_session.add(dest)
    db_session.commit()
    db_session.refresh(dest)

    alarm = Alarm(
        user_id=test_user.id,
        destination_id=dest.id,
        title="Calendar Linked Alarm",
        arrival_time=time(9, 0),
        calendar_event_id="google-evt-cancelled",
        status=AlarmStatus.SCHEDULED,
        enabled=True,
    )
    db_session.add(alarm)
    db_session.commit()

    conn = cal_repo.create_connection(
        user_id=test_user.id,
        account_email="user@gmail.com",
        encrypted_access_token=encrypt_token("tok"),
        encrypted_refresh_token=None,
        token_expires_at=None,
    )

    event, _ = cal_repo.upsert_event(
        connection_id=conn.id,
        user_id=test_user.id,
        external_event_id="google-evt-cancelled",
        title="Cancelled Team Meeting",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        timezone_str="UTC",
        status="cancelled",
    )
    cal_repo.link_alarm_to_event(event.id, alarm.id)

    context_svc = ContextService(
        alarm_repo=alarm_repo,
        destination_repo=dest_repo,
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=cal_repo,
    )

    results = await context_svc.evaluate_alarm_context(alarm.id)
    cal_res = next(r for r in results if r.context_type == ContextType.CALENDAR)

    assert cal_res.finding == ContextFinding.CALENDAR_EVENT_CANCELLED
    assert cal_res.recommended_action == ContextAction.WARN_USER
    # Alarm is preserved (not silently deleted)
    assert alarm_repo.get(alarm.id) is not None


# ===========================================================================
# 4. Security, IDOR, & Stale Writes Tests (Sections 11, 16, 24)
# ===========================================================================

def test_cross_user_calendar_isolation_forbidden(
    client: TestClient, other_client: TestClient, db_session: Session
):
    """Section 24: User B cannot view or disconnect User A's calendar connection."""
    user = db_session.query(User).filter(User.email == "tester@ada-alarm.com").first()
    cal_repo = CalendarRepository(db_session)
    conn = cal_repo.create_connection(
        user_id=user.id,
        account_email="private_a@gmail.com",
        encrypted_access_token=encrypt_token("tok_a"),
        encrypted_refresh_token=None,
        token_expires_at=None,
    )

    # User B tries to disconnect User A's connection -> 403 Forbidden
    del_res = other_client.delete(f"/api/v1/calendar/connections/{conn.id}")
    assert del_res.status_code in {403, 404}


@pytest.mark.asyncio
async def test_stale_context_update_rejected(
    client: TestClient, charusat_destination: dict, db_session: Session
):
    """Section 16: Concurrency / version protection prevents stale context overwrites."""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    res = client.post(
        "/api/v1/alarms",
        json={
            "title": "Stale Context Protection Alarm",
            "destination_id": charusat_destination["id"],
            "arrival_time": "09:00:00",
            "arrival_date": tomorrow.isoformat(),
            "preparation_time": 30,
            "safety_buffer": 10,
        },
    )
    alarm_id = uuid.UUID(res.json()["id"])
    alarm_repo = AlarmRepository(db_session)

    # Simulate an update moving schedule_version to 2
    alarm = alarm_repo.get(alarm_id)
    alarm.schedule_version = 2
    db_session.commit()

    context_svc = ContextService(
        alarm_repo=alarm_repo,
        destination_repo=DestinationRepository(db_session),
        pref_repo=PreferenceRepository(db_session),
        calendar_repo=CalendarRepository(db_session),
    )

    # Stale client requests adjustment with expected_version = 1
    recalc_result = await context_svc.apply_weather_buffer(
        alarm_id=alarm_id,
        user_id=alarm.user_id,
        buffer_minutes=10,
        expected_version=1,
    )

    assert recalc_result.status == "stale_rejected"
    assert recalc_result.schedule_changed is False
