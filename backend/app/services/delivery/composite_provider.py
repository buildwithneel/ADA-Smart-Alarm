from __future__ import annotations

import logging
from typing import List, Optional

from app.models.notification import Notification, NotificationChannel
from app.models.preference import UserPreference
from app.services.delivery.base import DeliveryResult, NotificationDeliveryProvider

logger = logging.getLogger("ada.delivery.composite")


class CompositeNotificationProvider(NotificationDeliveryProvider):
    """
    Coordinates delivery across multiple registered notification channels
    (e.g., In-App, Web Push, Native Bridge).
    """

    def __init__(self, providers: List[NotificationDeliveryProvider]):
        self.providers = providers

    @property
    def provider_name(self) -> str:
        return "composite"

    async def deliver(
        self, notification: Notification, user_pref: Optional[UserPreference] = None
    ) -> DeliveryResult:
        successes = 0
        failures = 0
        last_error = None
        is_transient = False

        for provider in self.providers:
            # Respect targeted notification channels
            if notification.channel == NotificationChannel.IN_APP and provider.provider_name != "in_app":
                continue
            if notification.channel == NotificationChannel.WEB_PUSH and provider.provider_name != "web_push":
                continue

            try:
                result = await provider.deliver(notification, user_pref)
                if result.success:
                    successes += 1
                else:
                    failures += 1
                    last_error = result.error_message
                    if result.is_transient:
                        is_transient = True
            except Exception as exc:
                logger.error(
                    f"Unhandled error in provider {provider.provider_name} for notification {notification.id}: {exc}",
                    exc_info=True,
                )
                failures += 1
                last_error = str(exc)
                is_transient = True

        # In-app success guarantees that the notification is preserved and visible to user
        if successes > 0:
            return DeliveryResult(success=True, provider_name=self.provider_name)

        return DeliveryResult(
            success=False,
            provider_name=self.provider_name,
            error_message=last_error or "Delivery failed on all channels",
            is_transient=is_transient,
        )
