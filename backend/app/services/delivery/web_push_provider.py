from __future__ import annotations

import base64
import json
import logging
from typing import Optional

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from app.core.config import settings
from app.models.notification import Notification
from app.models.preference import UserPreference
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.services.delivery.base import DeliveryResult, NotificationDeliveryProvider

logger = logging.getLogger("ada.delivery.web_push")

# In-memory singleton fallback VAPID keypair for dev/test environments
_DEV_VAPID_INSTANCE: Optional[Vapid] = None


def get_vapid_manager() -> tuple[Vapid, str]:
    """
    Returns (vapid_instance, public_key_base64url).
    Loads from settings if configured, else maintains a persistent in-process dev keypair.
    """
    global _DEV_VAPID_INSTANCE

    if settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY:
        try:
            v = Vapid.from_string(settings.VAPID_PRIVATE_KEY)
            return v, settings.VAPID_PUBLIC_KEY
        except Exception as e:
            logger.warning(f"Failed to load VAPID key from settings ({e}), falling back to dev key")

    if _DEV_VAPID_INSTANCE is None:
        _DEV_VAPID_INSTANCE = Vapid()
        _DEV_VAPID_INSTANCE.generate_keys()

    raw_pub = _DEV_VAPID_INSTANCE.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    b64_pub = base64.urlsafe_b64encode(raw_pub).decode().rstrip("=")
    return _DEV_VAPID_INSTANCE, b64_pub


class WebPushNotificationProvider(NotificationDeliveryProvider):
    """
    W3C Web Push API provider using RFC 8291 payload encryption and RFC 8292 VAPID authentication.
    Handles automatic cleanup of expired/revoked subscriptions (HTTP 410 Gone / 404).
    """

    def __init__(self, push_repo: PushSubscriptionRepository):
        self.push_repo = push_repo

    @property
    def provider_name(self) -> str:
        return "web_push"

    @classmethod
    def get_public_key(cls) -> str:
        _, pub = get_vapid_manager()
        return pub

    async def deliver(
        self, notification: Notification, user_pref: Optional[UserPreference] = None
    ) -> DeliveryResult:
        if user_pref and not user_pref.web_push_enabled:
            logger.info(
                f"Web Push skipped for notification {notification.id}: disabled in user preferences"
            )
            return DeliveryResult(
                success=True,
                provider_name=self.provider_name,
                error_message="Skipped by user preference",
            )

        subscriptions = self.push_repo.get_active_by_user(notification.user_id)
        if not subscriptions:
            logger.info(
                f"No active Web Push subscriptions found for user {notification.user_id}; in-app delivery will suffice"
            )
            return DeliveryResult(
                success=True,
                provider_name=self.provider_name,
                error_message="No active push subscriptions registered",
            )

        vapid_inst, _ = get_vapid_manager()
        claims = {
            "sub": settings.VAPID_CLAIMS_EMAIL,
        }

        payload_dict = {
            "id": str(notification.id),
            "alarm_id": str(notification.alarm_id) if notification.alarm_id else None,
            "type": notification.type.value,
            "title": notification.title,
            "body": notification.body,
            "scheduled_for": notification.scheduled_for.isoformat(),
            "data": {
                "action_url": notification.metadata_json.get("action_url", "/alarms"),
                "alarm_id": str(notification.alarm_id) if notification.alarm_id else None,
                "type": notification.type.value,
            },
        }
        payload_data = json.dumps(payload_dict)

        delivered_any = False
        last_error = None
        is_transient = False

        for sub in subscriptions:
            subscription_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh_key,
                    "auth": sub.auth_key,
                },
            }
            try:
                # pywebpush performs RFC 8291 AES-GCM encryption & VAPID signing
                response = webpush(
                    subscription_info=subscription_info,
                    data=payload_data,
                    vapid_private_key=vapid_inst,
                    vapid_claims=claims,
                    ttl=3600,
                )
                delivered_any = True
                logger.info(
                    f"Web Push sent to endpoint {sub.endpoint[:40]}...: status={getattr(response, 'status_code', 201)}"
                )
            except WebPushException as exc:
                status_code = getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None
                logger.warning(
                    f"Web Push delivery error for endpoint {sub.endpoint[:40]}...: status={status_code}, error={exc}"
                )
                if status_code in (404, 410):
                    # Subscription is expired or revoked by user browser
                    logger.info(f"Deactivating stale push subscription {sub.id} (HTTP {status_code})")
                    self.push_repo.deactivate(sub.endpoint)
                elif status_code in (429, 500, 502, 503, 504):
                    is_transient = True
                    last_error = f"HTTP {status_code} transient gateway error"
                else:
                    last_error = str(exc)
            except Exception as exc:
                logger.error(f"Unexpected error sending Web Push to {sub.endpoint[:40]}...: {exc}")
                last_error = str(exc)
                is_transient = True

        if delivered_any or not subscriptions:
            return DeliveryResult(success=True, provider_name=self.provider_name)

        return DeliveryResult(
            success=False,
            provider_name=self.provider_name,
            error_message=last_error or "All subscription deliveries failed",
            is_transient=is_transient,
        )
