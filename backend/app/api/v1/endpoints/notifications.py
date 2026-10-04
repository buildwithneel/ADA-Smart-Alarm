from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_notification_service
from app.core.errors import NotFoundException
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationTestRequest,
    PushSubscriptionCreate,
    PushSubscriptionResponse,
    VapidKeyResponse,
)
from app.services.delivery.web_push_provider import WebPushNotificationProvider
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Max notifications to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """
    Retrieves chronological notification history for the authenticated user.
    """
    items, total, unread_count = service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count")
def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    """
    Returns unread notification badge count for navigation header.
    """
    count = service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """
    Marks a specific notification as read.
    """
    updated = service.mark_notification_read(notification_id, current_user.id)
    if not updated:
        raise NotFoundException("Notification", notification_id)
    return NotificationResponse.model_validate(updated)


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    """
    Marks all pending and delivered notifications as read for the authenticated user.
    """
    count = service.mark_all_notifications_read(current_user.id)
    return {"marked_read": count}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """
    Fetches the user's notification preferences.
    """
    return service.get_preferences(current_user.id)


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    pref_update: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """
    Updates the user's notification preferences (wake, departure, changes, sounds).
    """
    return service.update_preferences(current_user.id, pref_update)


@router.get("/push/vapid-key", response_model=VapidKeyResponse)
def get_vapid_public_key(
    current_user: User = Depends(get_current_user),
) -> VapidKeyResponse:
    """
    Returns the server's public VAPID key so the browser can register with PushManager.
    """
    return VapidKeyResponse(public_key=WebPushNotificationProvider.get_public_key())


@router.post(
    "/push/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_push_subscription(
    sub_data: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> PushSubscriptionResponse:
    """
    Registers a browser Web Push subscription for the authenticated user.
    """
    sub = service.register_push_subscription(
        user_id=current_user.id,
        endpoint=sub_data.endpoint,
        p256dh=sub_data.p256dh,
        auth=sub_data.auth,
        user_agent=sub_data.user_agent,
    )
    return PushSubscriptionResponse.model_validate(sub)


@router.delete("/push/subscribe")
def unregister_push_subscription(
    endpoint: str = Query(..., description="Browser push subscription endpoint to revoke"),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, str]:
    """
    Unregisters/revokes a browser Web Push subscription.
    """
    success = service.unregister_push_subscription(current_user.id, endpoint)
    return {"status": "unsubscribed" if success else "not_found"}


@router.post(
    "/test",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_test_notification(
    test_req: NotificationTestRequest,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """
    Dispatches a test notification to verify active in-app and Web Push delivery channels.
    """
    notif = await service.send_test_notification(current_user.id, test_req)
    return NotificationResponse.model_validate(notif)
