from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Tuple, Union
from .base import BaseRepository
from ..models import Conversation, Message


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

    def get_user_conversations(
        self, user_id: int
    ) -> List[Tuple[Conversation, Message]]:
        """Get all conversations for a user with their latest messages"""
        return (
            self.db.query(Conversation, Message)
            .filter(Conversation.user_id == user_id)
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .order_by(Conversation.created_at.desc(), Message.created_at.desc())
            .all()
        )

    def get_conversation_with_messages(
        self, conversation_id: int
    ) -> Union[Conversation, None]:
        """Get a conversation with all its messages"""
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
