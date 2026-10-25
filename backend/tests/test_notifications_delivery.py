import asyncio
import uuid
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.alarm import Alarm, AlarmStatus, TransportMode
from app.models.destination import Destination, DestinationType
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.preference import UserPreference
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.services.delivery.base import DeliveryResult, NotificationDeliveryProvider
from app.services.notification_service import NotificationService
from app.worker.tasks import deliver_due_notifications, deliver_single_notification


@pytest.fixture
def test_user(db_session):
    u = User(
        firebase_uid="firebase-notif-user-1",
        email="notifuser@example.com",
        name="Notif User",
        timezone="Asia/Kolkata",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    pref = UserPreference(
        user_id=u.id,
        wake_alarm_enabled=True,
        departure_reminder_enabled=True,
        departure_reminder_lead_minutes=10,
        schedule_change_enabled=True,
        traffic_change_enabled=True,
        sound_enabled=True,
        vibration_enabled=True,
        in_app_enabled=True,
        web_push_enabled=True,
    )
    db_session.add(pref)
    db_session.commit()
    return u


@pytest.fixture
def other_user(db_session):
    u = User(
        firebase_uid="firebase-other-user-2",
        email="othernotif@example.com",
        name="Other User",
        timezone="Asia/Kolkata",
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def test_dest(db_session, test_user):
    d = Destination(
        user_id=test_user.id,
        name="CHARUSAT Campus",
        address="Anand, Gujarat",
        latitude=22.5996,
        longitude=72.8205,
        type=DestinationType.OFFICE,
    )
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    return d


@pytest.fixture
def active_alarm(db_session, test_user, test_dest):
    now = datetime.now(timezone.utc)
    arrival_dt = (now + timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
    travel_mins = 35
    safety_mins = 10
    prep_mins = 30

    leave_dt = arrival_dt - timedelta(minutes=travel_mins + safety_mins)
    wake_dt = leave_dt - timedelta(minutes=prep_mins)

    alarm = Alarm(
        user_id=test_user.id,
        destination_id=test_dest.id,
        title="Morning Lecture",
        arrival_time=arrival_dt.time(),
        planned_arrival_time=arrival_dt - timedelta(minutes=safety_mins),
        calculated_leave_time=leave_dt,
        calculated_wake_time=wake_dt,
        transportation_mode=TransportMode.DRIVING,
        preparation_time=prep_mins,
        safety_buffer=safety_mins,
        current_travel_minutes=travel_mins,
        traffic_delay_minutes=0,
        schedule_version=1,
        status=AlarmStatus.ACTIVE,
        enabled=True,
    )
    db_session.add(alarm)
    db_session.commit()
    db_session.refresh(alarm)
    return alarm


# =============================================================================
# 1. Alarm Event Scheduling & Due Event Detection
# =============================================================================

def test_step9_alarm_event_scheduling(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    created = service.schedule_alarm_notifications(active_alarm)

    assert len(created) == 2
    wake_notif = next(n for n in created if n.type == NotificationType.ALARM_WAKE)
    dept_notif = next(n for n in created if n.type == NotificationType.ALARM_DEPARTURE_REMINDER)

    assert wake_notif.status == NotificationStatus.PENDING
    assert wake_notif.schedule_version == 1
    assert "CHARUSAT" in wake_notif.body
    assert wake_notif.idempotency_key == f"alarm:{active_alarm.id}:v1:wake"

    assert dept_notif.status == NotificationStatus.PENDING
    assert dept_notif.schedule_version == 1
    assert "10 minutes" in dept_notif.body


def test_step9_due_event_detection_and_delivery(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    service.schedule_alarm_notifications(active_alarm)

    # Fast forward scheduled_for to past
    due_wake = db_session.query(Notification).filter_by(
        alarm_id=active_alarm.id, type=NotificationType.ALARM_WAKE
    ).first()
    due_wake.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    # Process due notifications
    stats = asyncio.run(service.process_due_notifications())
    assert stats["delivered"] >= 1

    db_session.refresh(due_wake)
    assert due_wake.status == NotificationStatus.DELIVERED
    assert due_wake.delivered_at is not None


# =============================================================================
# 2. Duplicate Delivery Prevention & Idempotency
# =============================================================================

def test_step9_duplicate_delivery_prevention(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    service.schedule_alarm_notifications(active_alarm)

    # Calling scheduling again must be idempotent (no duplicate notifications created)
    second_run = service.schedule_alarm_notifications(active_alarm)
    assert len(second_run) == 0

    all_notifs = db_session.query(Notification).filter_by(alarm_id=active_alarm.id).all()
    assert len(all_notifs) == 2


# =============================================================================
# 3. Retry Behavior & Final Failure
# =============================================================================

def test_step9_retry_behavior_and_final_failure(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    # Mock failing delivery provider
    failing_provider = MagicMock(spec=NotificationDeliveryProvider)
    failing_provider.provider_name = "mock_failing"
    failing_provider.deliver = AsyncMock(
        return_value=DeliveryResult(
            success=False,
            provider_name="mock_failing",
            error_message="Gateway timeout 504",
            is_transient=True,
        )
    )

    service = NotificationService(
        notif_repo, push_repo, alarm_repo, pref_repo, delivery_provider=failing_provider
    )

    notif = Notification(
        user_id=test_user.id,
        alarm_id=active_alarm.id,
        type=NotificationType.ALARM_WAKE,
        status=NotificationStatus.PENDING,
        channel=NotificationChannel.ALL,
        title="Test Wake",
        body="Wake up",
        scheduled_for=datetime.now(timezone.utc),
        schedule_version=1,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    # Attempt 1: Should schedule retry with backoff
    res1 = asyncio.run(service.deliver_notification(notif.id))
    assert res1.success is False
    db_session.refresh(notif)
    assert notif.retry_count == 1
    assert notif.status == NotificationStatus.PENDING

    # Fast-forward retry attempts up to MAX_NOTIFICATION_RETRIES (3)
    notif.retry_count = 2
    db_session.commit()

    res3 = asyncio.run(service.deliver_notification(notif.id))
    assert res3.success is False
    db_session.refresh(notif)
    assert notif.retry_count == 3
    assert notif.status == NotificationStatus.FAILED
    assert "Gateway timeout" in notif.last_error


# =============================================================================
# 4. Critical Delivery Test: Rescheduling & Superseding (Section 38)
# =============================================================================

def test_step9_critical_delivery_test_schedule_superseding(db_session, test_user, active_alarm):
    """
    Initial alarm: Wake 7:45 AM (v1).
    Traffic update: Wake shifts to 7:25 AM (v2).
    The old 7:45 event must become SUPERSEDED.
    The new 7:25 event must be PENDING.
    Only the 7:25 event delivers.
    """
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    service.schedule_alarm_notifications(active_alarm)

    v1_wake = db_session.query(Notification).filter_by(
        alarm_id=active_alarm.id, type=NotificationType.ALARM_WAKE, schedule_version=1
    ).first()
    assert v1_wake.status == NotificationStatus.PENDING

    # Step 8 triggers traffic recalculation: version 1 -> 2
    old_wake = active_alarm.calculated_wake_time
    new_wake = old_wake - timedelta(minutes=20)
    active_alarm.calculated_wake_time = new_wake
    active_alarm.calculated_leave_time = active_alarm.calculated_leave_time - timedelta(minutes=20)
    active_alarm.schedule_version = 2
    db_session.commit()

    change_notif = asyncio.run(
        service.handle_schedule_changed(
            alarm=active_alarm,
            previous_wake=old_wake,
            new_wake=new_wake,
            change_reason="TRAFFIC_INCREASE",
            is_urgent=False,
        )
    )

    db_session.refresh(v1_wake)
    # 1. Obsolete v1 wake notification is now SUPERSEDED
    assert v1_wake.status == NotificationStatus.SUPERSEDED

    # 2. Immediate change notification was created and delivered
    assert change_notif.status == NotificationStatus.DELIVERED
    assert change_notif.type == NotificationType.ALARM_SCHEDULE_CHANGED

    # 3. New v2 wake notification is scheduled as PENDING
    v2_wake = db_session.query(Notification).filter_by(
        alarm_id=active_alarm.id, type=NotificationType.ALARM_WAKE, schedule_version=2
    ).first()
    assert v2_wake is not None
    assert v2_wake.status == NotificationStatus.PENDING
    assert v2_wake.scheduled_for.replace(tzinfo=None) == new_wake.replace(tzinfo=None)


# =============================================================================
# 5. Missed Alarm & Urgent Update (Section 39)
# =============================================================================

def test_step9_missed_recalculation_urgent_alert(db_session, test_user, active_alarm):
    """
    Traffic surge causes new wake time to already be in the past.
    Generates ALARM_URGENT_CHANGE with actionable notice.
    """
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)

    old_wake = active_alarm.calculated_wake_time
    past_wake = datetime.now(timezone.utc) - timedelta(minutes=15)
    active_alarm.calculated_wake_time = past_wake
    active_alarm.schedule_version = 3
    db_session.commit()

    change_notif = asyncio.run(
        service.handle_schedule_changed(
            alarm=active_alarm,
            previous_wake=old_wake,
            new_wake=past_wake,
            change_reason="URGENT_SCHEDULE_CHANGE",
            is_urgent=True,
        )
    )

    assert change_notif.type == NotificationType.ALARM_URGENT_CHANGE
    assert "Urgent Schedule Change" in change_notif.title
    assert "already passed" in change_notif.body


# =============================================================================
# 6. Disabled & Expired Alarms Cancel Pending Events
# =============================================================================

def test_step9_disabled_alarm_cancels_pending(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    service.schedule_alarm_notifications(active_alarm)

    cancelled_count = service.handle_alarm_disabled_or_cancelled(
        active_alarm.id, reason="User turned off alarm"
    )
    assert cancelled_count >= 1

    pending = db_session.query(Notification).filter_by(
        alarm_id=active_alarm.id, status=NotificationStatus.PENDING
    ).all()
    assert len(pending) == 0


# =============================================================================
# 7. Notification Preferences Enforcement
# =============================================================================

def test_step9_notification_preferences_enforced(db_session, test_user, active_alarm):
    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)

    # User turns off wake alarms in preferences
    pref = pref_repo.get_by_user(test_user.id)
    pref.wake_alarm_enabled = False
    pref_repo.update(pref)

    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)
    service.schedule_alarm_notifications(active_alarm)

    wake_notif = db_session.query(Notification).filter_by(
        alarm_id=active_alarm.id, type=NotificationType.ALARM_WAKE
    ).first()

    # Deliver attempt should cancel due to user preference
    res = asyncio.run(service.deliver_notification(wake_notif.id))
    assert res.success is True

    db_session.refresh(wake_notif)
    assert wake_notif.status == NotificationStatus.CANCELLED
    assert "Wake alarms disabled" in wake_notif.last_error


# =============================================================================
# 8. Web Push Subscriptions CRUD & Stale Revocation (HTTP 410)
# =============================================================================

def test_step9_push_subscription_lifecycle_and_410_cleanup(db_session, test_user):
    push_repo = PushSubscriptionRepository(db_session)

    # 1. Register subscription
    sub = push_repo.create_or_update(
        user_id=test_user.id,
        endpoint="https://fcm.googleapis.com/fcm/send/fake-sub-token-123",
        p256dh="BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9t0AxdSSS99KxGoNVTzpIO_HQYZMp10keqe1",
        auth="tBHItJI5svbpez7KI4CCXg",
        user_agent="Mozilla/5.0 Chrome",
    )
    assert sub.is_active is True

    # 2. Deactivate on 410 Gone / 404
    push_repo.deactivate(sub.endpoint)
    db_session.refresh(sub)
    assert sub.is_active is False

    # 3. Reactivate on re-subscribe
    reactivated = push_repo.create_or_update(
        user_id=test_user.id,
        endpoint="https://fcm.googleapis.com/fcm/send/fake-sub-token-123",
        p256dh="new-p256dh",
        auth="new-auth",
    )
    assert reactivated.is_active is True

    # 4. Delete subscription
    deleted = push_repo.delete_by_user_and_endpoint(test_user.id, sub.endpoint)
    assert deleted is True


# =============================================================================
# 9. Cross-User Isolation (Security)
# =============================================================================

def test_step9_cross_user_isolation(db_session, test_user, other_user, active_alarm, client):
    notif_repo = NotificationRepository(db_session)
    notif = Notification(
        user_id=test_user.id,
        alarm_id=active_alarm.id,
        type=NotificationType.ALARM_WAKE,
        status=NotificationStatus.DELIVERED,
        channel=NotificationChannel.ALL,
        title="Secret User A Alarm",
        body="Wake up User A",
        scheduled_for=datetime.now(timezone.utc),
    )
    notif_repo.create(notif)

    # Authenticate as User B
    with patch("app.services.firebase_auth_service.FirebaseAuthService.verify_id_token") as mock_auth:
        mock_auth.return_value = {
            "uid": other_user.firebase_uid,
            "email": other_user.email,
            "name": other_user.name,
        }
        headers = {"Authorization": "Bearer mock-token-user-b"}

        # User B reads notifications -> Should not contain User A's notification
        res = client.get("/api/v1/notifications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert not any(item["id"] == str(notif.id) for item in data["items"])

        # User B attempts to mark User A's notification as read -> 404 Not Found
        mark_res = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert mark_res.status_code == 404


# =============================================================================
# 10. API: Mark Read, Mark All Read & Unread Count
# =============================================================================

def test_step9_api_read_and_unread_count(db_session, test_user, client):
    notif_repo = NotificationRepository(db_session)
    now = datetime.now(timezone.utc)
    for i in range(3):
        notif = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            status=NotificationStatus.DELIVERED,
            channel=NotificationChannel.ALL,
            title=f"Notification {i}",
            body=f"Body {i}",
            scheduled_for=now,
        )
        notif_repo.create(notif)

    with patch("app.services.firebase_auth_service.FirebaseAuthService.verify_id_token") as mock_auth:
        mock_auth.return_value = {
            "uid": test_user.firebase_uid,
            "email": test_user.email,
            "name": test_user.name,
        }
        headers = {"Authorization": "Bearer mock-token-user-a"}

        # Check unread count
        count_res = client.get("/api/v1/notifications/unread-count", headers=headers)
        assert count_res.status_code == 200
        assert count_res.json()["unread_count"] == 3

        # Mark all read
        read_all_res = client.post("/api/v1/notifications/read-all", headers=headers)
        assert read_all_res.status_code == 200
        assert read_all_res.json()["marked_read"] == 3

        # Check unread count again -> 0
        count_res2 = client.get("/api/v1/notifications/unread-count", headers=headers)
        assert count_res2.json()["unread_count"] == 0


# =============================================================================
# 11. Timezone, Midnight & Previous-Day Wake
# =============================================================================

def test_step9_timezone_midnight_and_previous_day_wake(db_session, test_user, test_dest):
    """
    Desired arrival is 00:30 AM (just past midnight).
    Travel: 45 min, Buffer: 15 min, Preparation: 40 min -> Total lead time: 100 min.
    Wake time falls on 22:50 PM the PREVIOUS calendar day.
    Ambiguity-free timezone datetime must be preserved.
    """
    tz = ZoneInfo("Asia/Kolkata")
    today = datetime.now(tz).date()
    tomorrow = today + timedelta(days=1)
    arrival_time = time(0, 30)

    arrival_dt = datetime.combine(tomorrow, arrival_time, tzinfo=tz)
    total_lead_mins = 45 + 15 + 40  # 100 min
    wake_dt = arrival_dt - timedelta(minutes=total_lead_mins)
    leave_dt = arrival_dt - timedelta(minutes=45 + 15)

    assert wake_dt.date() == today  # Wake is on previous day!

    alarm = Alarm(
        user_id=test_user.id,
        destination_id=test_dest.id,
        title="Midnight Shift",
        arrival_time=arrival_time,
        planned_arrival_time=arrival_dt - timedelta(minutes=15),
        calculated_leave_time=leave_dt,
        calculated_wake_time=wake_dt,
        transportation_mode=TransportMode.DRIVING,
        preparation_time=40,
        safety_buffer=15,
        current_travel_minutes=45,
        schedule_version=1,
        status=AlarmStatus.ACTIVE,
        enabled=True,
    )
    db_session.add(alarm)
    db_session.commit()
    db_session.refresh(alarm)

    notif_repo = NotificationRepository(db_session)
    push_repo = PushSubscriptionRepository(db_session)
    alarm_repo = AlarmRepository(db_session)
    pref_repo = PreferenceRepository(db_session)
    service = NotificationService(notif_repo, push_repo, alarm_repo, pref_repo)

    created = service.schedule_alarm_notifications(alarm)
    wake_notif = next(n for n in created if n.type == NotificationType.ALARM_WAKE)

    scheduled = (
        wake_notif.scheduled_for.replace(tzinfo=tz)
        if wake_notif.scheduled_for.tzinfo is None
        else wake_notif.scheduled_for.astimezone(tz)
    )
    assert scheduled.date() == today
    assert scheduled.hour == 22
    assert scheduled.minute == 50


# =============================================================================
# 12. Celery Worker Task Execution
# =============================================================================

def test_step9_celery_notification_tasks(db_session, test_user, active_alarm):
    from sqlalchemy.orm import sessionmaker
    session_factory = sessionmaker(bind=db_session.get_bind())

    notif_repo = NotificationRepository(db_session)
    notif = Notification(
        user_id=test_user.id,
        alarm_id=active_alarm.id,
        type=NotificationType.ALARM_WAKE,
        status=NotificationStatus.PENDING,
        channel=NotificationChannel.IN_APP,
        title="Celery Wake Test",
        body="Good morning",
        scheduled_for=datetime.now(timezone.utc) - timedelta(seconds=10),
        schedule_version=1,
    )
    notif_repo.create(notif)

    with patch("app.worker.tasks.SessionLocal", side_effect=session_factory):
        # Execute periodic sweep task
        sweep_res = deliver_due_notifications()
        assert sweep_res["status"] == "success"
        assert sweep_res["delivered"] >= 1

    check_session = session_factory()
    db_notif = check_session.query(Notification).filter_by(id=notif.id).first()
    assert db_notif is not None
    assert db_notif.status == NotificationStatus.DELIVERED
    check_session.close()
