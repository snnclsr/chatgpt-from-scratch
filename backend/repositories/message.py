from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Union
from .base import BaseRepository
from ..models import Message


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(Message, db)

    def get_conversation_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation ordered by creation time"""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def get_latest_message(self, conversation_id: int) -> Union[Message, None]:
        """Get the latest message in a conversation"""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .first()
        )
