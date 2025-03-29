from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.routes import router
from app.database import SessionLocal, engine
from app import models
from app.schemas import (
    ChatInput,
    ChatResponse,
    ConversationResponse,
    HealthResponse,
    StreamingChatInput,
)
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.user_service import UserService
from app.services.llm_service import LLMService
import logging

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


@app.post(
    "/api/chat/stream",
    description="""
    Streaming chat endpoint that returns tokens one by one as they are generated.
    
    This endpoint follows the Server-Sent Events (SSE) protocol. Each token is sent 
    as a separate 'data:' message. The stream ends with 'data: [DONE]'.
    
    The response from the LLM will be streamed token by token, allowing for a more 
    interactive experience. After the streaming is complete, the full response is 
    stored in the database.
    
    The streaming parameters (max_length, temperature, top_p) are optional and have 
    reasonable defaults.
    
    Client disconnection (e.g., CTRL+C) is handled gracefully. If the stream is interrupted,
    the partial response is NOT saved to the database.
    """,
)
async def chat_stream(message: StreamingChatInput, db: Session = Depends(get_db)):
    """Streaming chat endpoint that returns tokens one by one"""
    try:
        chat_service = ChatService(db)
        user_service = UserService(db)
        conversation_service = ConversationService(db)
        message_service = MessageService(db)
        llm_service = LLMService()

        # Get or create user
        user = user_service.get_or_create_default_user()

        # Get existing conversation or create new one
        if message.chat_id:
            conversation = conversation_service.get_conversation(message.chat_id)
            if not conversation:
                raise ValueError("Conversation not found")
        else:
            conversation = conversation_service.create_conversation(
                user.id, message.message
            )

        # Store user message
        message_service.create_message(
            content=message.message, role="user", conversation_id=conversation.id
        )

        # Get conversation history for context
        previous_messages = message_service.get_conversation_messages(conversation.id)

        # Format the prompt including conversation history
        formatted_prompt = chat_service._format_conversation_for_model(
            previous_messages
        )

        # Create a streaming response
        async def stream_generator():
            full_response = ""
            stream_completed = False

            try:
                async for token in llm_service.generate_stream(
                    prompt=formatted_prompt,
                    max_length=message.max_length,
                    temperature=message.temperature,
                    top_p=message.top_p,
                ):
                    if token.startswith("Error:"):
                        yield f"data: {token}\n\n"
                        break
                    full_response += token
                    yield f"data: {token}\n\n"

                # Mark stream as successfully completed
                stream_completed = True
                yield "data: [DONE]\n\n"

                # Only save the response if streaming completed successfully
                if stream_completed:
                    message_service.create_message(
                        content=full_response,
                        role="assistant",
                        conversation_id=conversation.id,
                    )
            except Exception as e:
                # Log any errors during streaming
                logging.error(f"Error during streaming: {str(e)}")
            finally:
                if not stream_completed:
                    # Log that the connection was terminated
                    logging.info(
                        f"Streaming connection terminated for conversation {conversation.id}. Response not saved."
                    )

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

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
