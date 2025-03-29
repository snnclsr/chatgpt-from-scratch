from sqlalchemy.orm import Session
from typing import Union
import logging
from .user_service import UserService
from .conversation_service import ConversationService
from .message_service import MessageService
from .llm_service import LLMService
from ..schemas import ChatResponse, ConversationResponse

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

        try:
            # Get conversation history for context
            previous_messages = self.message_service.get_conversation_messages(
                conversation.id
            )
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
        """Format the conversation history into a prompt for the model"""
        formatted_prompt = ""

        for message in messages:
            role = "User" if message.role == "user" else "Assistant"
            formatted_prompt += f"{role}: {message.content}\n"

        # Add final prompt for the assistant to respond
        formatted_prompt += "Assistant:"

        return formatted_prompt
