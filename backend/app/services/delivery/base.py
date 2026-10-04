from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

from app.models.notification import Notification
from app.models.preference import UserPreference


@dataclass
class DeliveryResult:
    """
    Standardized result for any delivery provider attempt.
    """

    success: bool
    provider_name: str
    error_message: Optional[str] = None
    is_transient: bool = False
    response_code: Optional[int] = None


class NotificationDeliveryProvider(abc.ABC):
    """
    Abstract Base Class for notification delivery channels.
    Decouples domain alarm events from delivery mediums (Web Push, In-App, native bridge, etc.).
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the delivery provider (e.g. 'in_app', 'web_push', 'native_mobile')."""
        pass

    @abc.abstractmethod
    async def deliver(
        self, notification: Notification, user_pref: Optional[UserPreference] = None
    ) -> DeliveryResult:
        """
        Dispatches the notification to the target medium.
        Returns DeliveryResult indicating success or failure status.
        """
        pass
