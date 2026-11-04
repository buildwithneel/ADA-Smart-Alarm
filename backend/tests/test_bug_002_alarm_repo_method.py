from app.repositories.alarm_repository import AlarmRepository
from app.repositories.destination_repository import DestinationRepository
from app.services.alarm_service import AlarmService


def test_alarm_repository_has_get_active_alarms_for_evaluation():
    """
    Regression test for BUG-002:
    Verify AlarmRepository exposes get_active_alarms_for_evaluation method.
    """
    assert hasattr(AlarmRepository, "get_active_alarms_for_evaluation")
    assert callable(getattr(AlarmRepository, "get_active_alarms_for_evaluation"))


def test_get_active_alarms_for_evaluation_execution(db_session):
    """
    Regression test for BUG-002:
    Verify get_active_alarms_for_evaluation retrieves active scheduled alarms
    and mark_expired_alarms runs cleanly without AttributeError.
    """
    alarm_repo = AlarmRepository(db_session)
    dest_repo = DestinationRepository(db_session)

    active_alarms = alarm_repo.get_active_alarms_for_evaluation(limit=10)
    assert isinstance(active_alarms, list)

    service = AlarmService(alarm_repo=alarm_repo, destination_repo=dest_repo)
    expired_count = service.mark_expired_alarms()
    assert isinstance(expired_count, int)
