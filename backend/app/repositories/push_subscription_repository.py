from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.push_subscription import PushSubscription
from app.repositories.base import BaseRepository

logger = logging.getLogger("ada.repositories.push_subscription")


class PushSubscriptionRepository(BaseRepository[PushSubscription]):
    """
    Repository for managing browser Web Push subscriptions, supporting
    ownership verification, deactivation on 410 Gone, and multi-device endpoints.
    """

    def __init__(self, db: Session):
        super().__init__(PushSubscription, db)

    def create_or_update(
        self,
        user_id: uuid.UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: Optional[str] = None,
    ) -> PushSubscription:
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        sub = self.db.scalars(stmt).first()

        if sub:
            # Transfer or reactivate subscription for the user
            sub.user_id = user_id
            sub.p256dh_key = p256dh
            sub.auth_key = auth
            sub.user_agent = user_agent
            sub.is_active = True
        else:
            sub = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh_key=p256dh,
                auth_key=auth,
                user_agent=user_agent,
                is_active=True,
            )
            self.db.add(sub)

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def get_by_endpoint(self, endpoint: str) -> Optional[PushSubscription]:
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        return self.db.scalars(stmt).first()

    def get_active_by_user(self, user_id: uuid.UUID) -> List[PushSubscription]:
        stmt = select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active == True,  # noqa: E712
        )
        return list(self.db.scalars(stmt).all())

    def deactivate(self, endpoint: str) -> bool:
        stmt = (
            update(PushSubscription)
            .where(PushSubscription.endpoint == endpoint)
            .values(is_active=False)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def delete_by_user_and_endpoint(self, user_id: uuid.UUID, endpoint: str) -> bool:
        stmt = delete(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0
