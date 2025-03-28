from sqlalchemy.orm import Session
from typing import Union
from .user_service import UserService
from .conversation_service import ConversationService
from .message_service import MessageService
from ..schemas import ChatResponse, ConversationResponse
import random


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.conversation_service = ConversationService(db)
        self.message_service = MessageService(db)

    # Temporary placeholder responses (will be replaced with AI integration)
    LOREM_RESPONSES = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    ]

    async def process_chat_message(
        self, message: str, chat_id: Union[int, None] = None
    ) -> ChatResponse:
        """Process a chat message and return the response"""
        # Get or create default user (temporary until auth is implemented)
        user = self.user_service.get_or_create_default_user()

        # Get existing conversation or create new one
        if chat_id:
            conversation = self.conversation_service.get_conversation(chat_id)
            if not conversation:
                raise ValueError("Conversation not found")
        else:
            conversation = self.conversation_service.create_conversation(
                user.id, message
            )

        # Store user message
        self.message_service.create_message(
            content=message, role="user", conversation_id=conversation.id
        )

        # Generate and store assistant response (temporary implementation)
        response_text = random.choice(self.LOREM_RESPONSES)
        assistant_message = self.message_service.create_message(
            content=response_text, role="assistant", conversation_id=conversation.id
        )

        # Get latest message for preview
        latest_message = self.message_service.get_latest_message(conversation.id)

        return ChatResponse(
            response=response_text,
            message_id=assistant_message.id,
            conversation=ConversationResponse(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                preview=latest_message.content if latest_message else None,
            ),
        )
