from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.core.errors import NotFoundException
from app.models.assistant import AssistantConversation, AssistantMessage
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.assistant import AssistantConversationResponse, AssistantMessageResponse
from app.services.base import BaseService

logger = logging.getLogger("ada.services.assistant_conversation")


class AssistantConversationService(BaseService):
    """Business service governing conversation lifecycle and privacy retention."""

    def __init__(
        self,
        assistant_repo: AssistantRepository,
        preference_repo: Optional[PreferenceRepository] = None,
    ):
        self.assistant_repo = assistant_repo
        self.preference_repo = preference_repo

    def get_or_create_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        title: str = "New Conversation",
    ) -> AssistantConversation:
        if conversation_id:
            conv = self.assistant_repo.get_conversation(user_id, conversation_id)
            if conv:
                return conv
            # If not found or belongs to another user, raise or create new
            raw_conv = self.assistant_repo.get(conversation_id)
            if raw_conv and raw_conv.user_id != user_id:
                logger.warning(
                    f"IDOR detected: User {user_id} requested conversation {conversation_id} owned by {raw_conv.user_id}"
                )
                raise NotFoundException("Conversation", conversation_id)

        # Check if conversation history is disabled
        return self.assistant_repo.create_conversation(user_id=user_id, title=title)

    def add_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssistantMessage:
        meta_str = json.dumps(metadata) if metadata else None
        return self.assistant_repo.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata_json=meta_str,
        )

    def list_conversations(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[AssistantConversationResponse]:
        convs = self.assistant_repo.list_conversations(user_id, skip=skip, limit=limit)
        return [
            AssistantConversationResponse(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                messages=[
                    AssistantMessageResponse.model_validate(m)
                    for m in (c.messages or [])
                ],
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ]

    def get_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> AssistantConversationResponse:
        conv = self.assistant_repo.get_conversation(user_id, conversation_id)
        if not conv:
            raw_conv = self.assistant_repo.get(conversation_id)
            if raw_conv and raw_conv.user_id != user_id:
                logger.warning(
                    f"IDOR detected: User {user_id} requested conversation {conversation_id} owned by {raw_conv.user_id}"
                )
            raise NotFoundException("Conversation", conversation_id)

        return AssistantConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            messages=[
                AssistantMessageResponse.model_validate(m) for m in (conv.messages or [])
            ],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def delete_conversation(
        self, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> bool:
        conv = self.assistant_repo.get_conversation(user_id, conversation_id)
        if not conv:
            raw_conv = self.assistant_repo.get(conversation_id)
            if raw_conv and raw_conv.user_id != user_id:
                logger.warning(
                    f"IDOR detected: User {user_id} requested delete for conversation {conversation_id}"
                )
            raise NotFoundException("Conversation", conversation_id)

        deleted = self.assistant_repo.delete_conversation(user_id, conversation_id)
        logger.info(f"Conversation {conversation_id} deleted by user {user_id}")
        return deleted

    def delete_all_conversations(self, user_id: uuid.UUID) -> int:
        count = self.assistant_repo.delete_all_conversations(user_id)
        logger.info(f"All {count} conversations deleted by user {user_id}")
        return count
