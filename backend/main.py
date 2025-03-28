from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api.routes import router
from app.core.config import settings
from app.database import SessionLocal, engine
from app import models
from app.schemas import ChatInput, ChatResponse, ConversationResponse, HealthResponse
import random
from typing import List
from sqlalchemy import desc

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Chat System")

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample titles and adjectives for random title generation
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


def generate_conversation_title(message: str) -> str:
    """Generate a title based on the message content or random words"""
    # Take first few words of the message if it's long enough
    words = message.split()
    if len(words) >= 3:
        title_from_message = " ".join(words[:3]) + "..."
        return title_from_message

    # If message is too short, generate a random title
    return f"{random.choice(ADJECTIVES)} {random.choice(TOPICS)}"


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.include_router(router)

# Placeholder responses
LOREM_RESPONSES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatInput, db: Session = Depends(get_db)):
    """
    Chat endpoint that stores messages in the database
    """
    # Create a default user if not exists (temporary solution)
    user = db.query(models.User).first()
    if not user:
        user = models.User(username="default_user")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get existing conversation or create new one
    if message.chat_id:
        conversation = (
            db.query(models.Conversation)
            .filter(models.Conversation.id == message.chat_id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation with generated title
        title = generate_conversation_title(message.message)
        conversation = models.Conversation(title=title, user_id=user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Store user message
    user_message = models.Message(
        content=message.message, role="user", conversation_id=conversation.id
    )
    db.add(user_message)

    # Generate and store assistant response
    response_text = random.choice(LOREM_RESPONSES)
    assistant_message = models.Message(
        content=response_text, role="assistant", conversation_id=conversation.id
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # Get the latest message for preview
    latest_message = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.created_at.desc())
        .first()
    )

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


@app.get("/api/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: int, db: Session = Depends(get_db)):
    """
    Get all messages for a specific chat
    """
    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == chat_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )

    if not messages:
        return []

    return [
        {
            "id": str(message.id),
            "content": message.content,
            "role": message.role,
            "timestamp": message.created_at.isoformat(),
        }
        for message in messages
    ]


@app.get("/api/conversations", response_model=list[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    """
    Get all conversations for the current user with their latest message as preview
    """
    user = db.query(models.User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query conversations with their latest message
    conversations = (
        db.query(models.Conversation, models.Message)
        .filter(models.Conversation.user_id == user.id)
        .outerjoin(
            models.Message, models.Message.conversation_id == models.Conversation.id
        )
        .order_by(
            models.Conversation.created_at.desc(), models.Message.created_at.desc()
        )
        .all()
    )

    # Group messages by conversation and take the latest one
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


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    return HealthResponse(status="ok")
