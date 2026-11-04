from unittest.mock import MagicMock, patch
from app.worker.tasks import evaluate_upcoming_weather_context
from app.core.config import settings


def test_evaluate_upcoming_weather_context_settings_access():
    """
    Regression test for BUG-001:
    Verify that evaluate_upcoming_weather_context accesses settings.UPCOMING_ALARM_WINDOW_SECONDS
    without raising NameError: name 'settings' is not defined.
    """
    with patch("app.worker.tasks.SessionLocal"), \
         patch("app.worker.tasks.AlarmRepository") as mock_alarm_repo_cls:
        mock_alarm_repo = MagicMock()
        mock_alarm_repo.get_upcoming_alarms.return_value = []
        mock_alarm_repo_cls.return_value = mock_alarm_repo

        result = evaluate_upcoming_weather_context()
        assert result["status"] == "success"
        assert result["evaluated_alarms"] == 0
        assert result["buffers_applied"] == 0
        mock_alarm_repo.get_upcoming_alarms.assert_called_once()
        window_arg = mock_alarm_repo.get_upcoming_alarms.call_args[1]["window_end"]
        assert window_arg is not None
