from __future__ import annotations

import logging
from typing import Optional

from app.models.notification import Notification
from app.models.preference import UserPreference
from app.services.delivery.base import DeliveryResult, NotificationDeliveryProvider

logger = logging.getLogger("ada.delivery.in_app")


class InAppNotificationProvider(NotificationDeliveryProvider):
    """
    In-App notification channel.
    Ensures notifications appear in the user's notification center drawer/feed.
    """

    @property
    def provider_name(self) -> str:
        return "in_app"

    async def deliver(
        self, notification: Notification, user_pref: Optional[UserPreference] = None
    ) -> DeliveryResult:
        if user_pref and not user_pref.in_app_enabled:
            logger.info(
                f"In-App delivery skipped for notification {notification.id}: disabled in user preferences"
            )
            return DeliveryResult(
                success=True,
                provider_name=self.provider_name,
                error_message="Skipped by user preference",
            )

        logger.info(
            f"Delivered in-app notification {notification.id} to user {notification.user_id}: '{notification.title}'"
        )
        return DeliveryResult(success=True, provider_name=self.provider_name)
