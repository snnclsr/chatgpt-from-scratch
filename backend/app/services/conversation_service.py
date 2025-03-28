from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union
from ..repositories.conversation import ConversationRepository
from ..models import Conversation
import random


class ConversationService:
    def __init__(self, db: Session):
        self.repository = ConversationRepository(db)

    # Sample data for title generation (moved from main.py)
    ADJECTIVES = [
        "Curious",
        "Insightful",
        "Thoughtful",
        "Engaging",
        "Interesting",
        "Creative",
        "Dynamic",
        "Exploratory",
        "Innovative",
        "Intriguing",
    ]

    TOPICS = [
        "Discussion",
        "Conversation",
        "Dialogue",
        "Chat",
        "Exchange",
        "Brainstorm",
        "Discovery",
        "Exploration",
        "Analysis",
        "Investigation",
    ]

    def generate_title(self, message: str) -> str:
        """Generate a title based on the message content or random words"""
        words = message.split()
        if len(words) >= 3:
            return " ".join(words[:3]) + "..."
        return f"{random.choice(self.ADJECTIVES)} {random.choice(self.TOPICS)}"

    def create_conversation(self, user_id: int, initial_message: str) -> Conversation:
        """Create a new conversation with a generated title"""
        title = self.generate_title(initial_message)
        return self.repository.create(title=title, user_id=user_id)

    def get_conversation(self, conversation_id: int) -> Union[Conversation, None]:
        """Get a conversation by ID"""
        return self.repository.get_conversation_with_messages(conversation_id)

    def get_user_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all conversations for a user with their latest messages"""
        conversations = self.repository.get_user_conversations(user_id)

        # Format the conversations for API response
        result = []
        seen_conversations = set()

        for conv, msg in conversations:
            if conv.id not in seen_conversations:
                seen_conversations.add(conv.id)
                result.append(
                    {
                        "id": conv.id,
                        "title": conv.title,
                        "created_at": conv.created_at.isoformat(),
                        "preview": msg.content if msg else None,
                    }
                )
        return result
