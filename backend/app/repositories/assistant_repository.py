from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.models.assistant import AlarmDraft, AssistantConversation, AssistantMessage, DraftStatus
from app.repositories.base import BaseRepository

logger = logging.getLogger("ada.repositories.assistant")


class AssistantRepository(BaseRepository[AssistantConversation]):
    """Repository managing Assistant Conversations, Messages, and Alarm Drafts."""

    def __init__(self, db: Session):
        super().__init__(AssistantConversation, db)

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    def create_conversation(
        self, user_id: uuid.UUID, title: str = "New Conversation"
    ) -> AssistantConversation:
        conv = AssistantConversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Optional[AssistantConversation]:
        stmt = (
            select(AssistantConversation)
            .options(joinedload(AssistantConversation.messages))
            .where(
                AssistantConversation.id == conversation_id,
                AssistantConversation.user_id == user_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def list_conversations(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[AssistantConversation]:
        stmt = (
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user_id)
            .order_by(desc(AssistantConversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def delete_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> bool:
        conv = self.get_conversation(user_id, conversation_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True

    def delete_all_conversations(self, user_id: uuid.UUID) -> int:
        stmt = select(AssistantConversation).where(
            AssistantConversation.user_id == user_id
        )
        convs = list(self.db.scalars(stmt).all())
        count = len(convs)
        for c in convs:
            self.db.delete(c)
        if count > 0:
            self.db.commit()
        return count

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        content: str,
        metadata_json: Optional[str] = None,
    ) -> AssistantMessage:
        msg = AssistantMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[AssistantMessage]:
        stmt = (
            select(AssistantMessage)
            .where(
                AssistantMessage.conversation_id == conversation_id,
                AssistantMessage.user_id == user_id,
            )
            .order_by(AssistantMessage.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # Alarm Drafts
    # ------------------------------------------------------------------

    def create_draft(self, draft: AlarmDraft) -> AlarmDraft:
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def get_draft(
        self, user_id: uuid.UUID, draft_id: uuid.UUID
    ) -> Optional[AlarmDraft]:
        stmt = select(AlarmDraft).where(
            AlarmDraft.id == draft_id,
            AlarmDraft.user_id == user_id,
        )
        return self.db.scalars(stmt).first()

    def get_any_draft_for_audit(self, draft_id: uuid.UUID) -> Optional[AlarmDraft]:
        stmt = select(AlarmDraft).where(AlarmDraft.id == draft_id)
        return self.db.scalars(stmt).first()

    def update_draft(self, draft: AlarmDraft) -> AlarmDraft:
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft
