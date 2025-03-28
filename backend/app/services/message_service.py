from sqlalchemy.orm import Session
from typing import List, Union, Dict
from ..repositories.message import MessageRepository
from ..models import Message


class MessageService:
    def __init__(self, db: Session):
        self.repository = MessageRepository(db)

    def create_message(self, content: str, role: str, conversation_id: int) -> Message:
        """Create a new message"""
        return self.repository.create(
            content=content, role=role, conversation_id=conversation_id
        )

    def get_conversation_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation"""
        return self.repository.get_conversation_messages(conversation_id)

    def get_latest_message(self, conversation_id: int) -> Union[Message, None]:
        """Get the latest message in a conversation"""
        return self.repository.get_latest_message(conversation_id)

    def format_messages_for_response(self, messages: List[Message]) -> List[Dict]:
        """Format messages for API response"""
        return [
            {
                "id": str(message.id),
                "content": message.content,
                "role": message.role,
                "timestamp": message.created_at.isoformat(),
            }
            for message in messages
        ]
