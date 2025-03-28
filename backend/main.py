from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api.routes import router
from app.core.config import settings
from app.database import SessionLocal, engine
from app import models
from app.schemas import ChatInput, ChatResponse, ConversationResponse, HealthResponse
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.user_service import UserService

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
    """Chat endpoint that processes messages using the chat service"""
    try:
        chat_service = ChatService(db)
        return await chat_service.process_chat_message(
            message=message.message, chat_id=message.chat_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: int, db: Session = Depends(get_db)):
    """Get all messages for a specific chat"""
    try:
        message_service = MessageService(db)
        messages = message_service.get_conversation_messages(chat_id)
        return message_service.format_messages_for_response(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations", response_model=list[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    """Get all conversations for the current user"""
    try:
        user_service = UserService(db)
        conversation_service = ConversationService(db)

        user = user_service.get_or_create_default_user()
        return conversation_service.get_user_conversations(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok")
