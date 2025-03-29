from sqlalchemy.orm import Session
from typing import Union, Dict, List
import logging
from functools import lru_cache
from .user_service import UserService
from .conversation_service import ConversationService
from .message_service import MessageService
from .llm_service import LLMService
from ..schemas import ChatResponse, ConversationResponse
from ..models import Conversation, Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.conversation_service = ConversationService(db)
        self.message_service = MessageService(db)
        # Initialize LLM service (singleton pattern ensures only one model instance)
        self.llm_service = LLMService()
        # Simple in-memory cache for conversation data
        self._conversation_cache: Dict[int, Conversation] = {}
        self._message_cache: Dict[int, List[Message]] = {}

    def _clear_cache_for_conversation(self, conversation_id: int) -> None:
        """Clear cached data for a specific conversation when it's modified"""
        if conversation_id in self._conversation_cache:
            del self._conversation_cache[conversation_id]
        if conversation_id in self._message_cache:
            del self._message_cache[conversation_id]

    def get_cached_conversation(self, conversation_id: int) -> Conversation:
        """Get conversation with caching to reduce database hits"""
        if conversation_id not in self._conversation_cache:
            conversation = self.conversation_service.get_conversation(conversation_id)
            if conversation:
                self._conversation_cache[conversation_id] = conversation
            return conversation
        return self._conversation_cache[conversation_id]

    def get_cached_messages(self, conversation_id: int) -> List[Message]:
        """Get conversation messages with caching to reduce database hits"""
        if conversation_id not in self._message_cache:
            messages = self.message_service.get_conversation_messages(conversation_id)
            self._message_cache[conversation_id] = messages
            return messages
        return self._message_cache[conversation_id]

    async def process_chat_message(
        self, message: str, chat_id: Union[int, None] = None
    ) -> ChatResponse:
        """Process a chat message and return the response"""
        # Get or create default user (temporary until auth is implemented)
        user = self.user_service.get_or_create_default_user()

        # Get existing conversation or create new one
        if chat_id:
            conversation = self.get_cached_conversation(chat_id)
            if not conversation:
                raise ValueError("Conversation not found")
        else:
            conversation = self.conversation_service.create_conversation(
                user.id, message
            )
            # Cache the new conversation
            self._conversation_cache[conversation.id] = conversation

        # Store user message
        self.message_service.create_message(
            content=message, role="user", conversation_id=conversation.id
        )
        # Clear cache since we've modified the conversation
        self._clear_cache_for_conversation(conversation.id)

        try:
            # Get conversation history for context
            previous_messages = self.get_cached_messages(conversation.id)
            # Format the prompt including conversation history
            prompt = self._format_conversation_for_model(previous_messages)
            logger.info(f"Prompt: {prompt}")
            # Generate response using the LLM service
            logger.info(
                f"Generating response for message in conversation {conversation.id}"
            )
            response_text = await self.llm_service.generate(
                prompt=prompt,
                max_length=200,  # Adjust as needed
                temperature=0.7,  # Adjust as needed
            )
            # Check for errors
            if response_text.startswith("Error:"):
                logger.error(f"LLM error: {response_text}")
                response_text = (
                    "I apologize, but I encountered an error processing your request."
                )

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            response_text = (
                "I apologize, but I encountered an error processing your request."
            )

        # Store assistant response
        assistant_message = self.message_service.create_message(
            content=response_text, role="assistant", conversation_id=conversation.id
        )
        # Clear cache since we've modified the conversation
        self._clear_cache_for_conversation(conversation.id)

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

    def _format_conversation_for_model(self, messages):
        return "\n".join([f"{message.content}" for message in messages])
        # """Format the conversation history into a prompt for the model"""
        # formatted_prompt = ""

        # for message in messages:
        #     role = "User" if message.role == "user" else "Assistant"
        #     formatted_prompt += f"{role}: {message.content}\n"

        # # Add final prompt for the assistant to respond
        # formatted_prompt += "Assistant:"

        # return formatted_prompt
