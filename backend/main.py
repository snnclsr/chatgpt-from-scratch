import uuid
import logging
from itertools import groupby
from typing import List, Dict, Any

import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import router
from app.database import SessionLocal, engine, get_db_context
from app import models
from app.schemas import (
    ConversationResponse,
    HealthResponse,
    WebSocketChatInput,
)
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.user_service import UserService
from app.services.llm_service import LLMService
# from routes.router import router as ws_router

from ml.factory import ModelFactory
from ml.config import MODEL_CONFIGS

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
# Register routes
app.include_router(router)
# app.include_router(ws_router, prefix="/api")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Connect a client and return its unique ID"""
        client_id = str(uuid.uuid4())
        await websocket.accept()
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        """Remove a client from active connections"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, client_id: str, message: dict):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, exclude: List[str] = None):
        """Send a message to all connected clients, optionally excluding some"""
        exclude = exclude or []
        for client_id, connection in self.active_connections.items():
            if client_id not in exclude:
                await connection.send_json(message)

    async def check_for_stop_command(
        self, client_id: str, timeout: float = 0.001
    ) -> bool:
        """Check if client has sent a stop command with a very short timeout"""
        if client_id not in self.active_connections:
            return False

        websocket = self.active_connections[client_id]
        try:
            # Non-blocking check for a stop message with a very short timeout
            data = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
            if data.get("command") == "stop":
                logging.info(f"Generation stopped by client request: {client_id}")
                return True
        except asyncio.TimeoutError:
            # No message received, continue generation
            pass
        return False


manager = ConnectionManager()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    # Register all models from config
    for model_id, config in MODEL_CONFIGS.items():
        logger.info(f"Registering model: {model_id}")
        await ModelFactory.get_model(model_id)
        # ModelFactory.register_model(model_id, config)


# @app.get("/")
# async def root():
#     return {
#         "status": "running",
#         "version": "1.0.0",
#         "docs_url": "/docs",
#         "models_url": "/api/models",
#     }


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


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a specific conversation"""
    try:
        conversation_service = ConversationService(db)
        if conversation_service.delete_conversation(conversation_id):
            return {"status": "success", "message": "Conversation deleted successfully"}
        raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok")


def _fix_gemma_messages(messages: List[Dict[str, Any]]):
    """Fix the Gemma messages to alternate user/assistant/user/assistant/"""
    grouped = []
    for role, group in groupby(messages, key=lambda x: x["role"]):
        contents = [msg["content"] for msg in group]
        merged = "\n".join(contents)
        grouped.append({"role": role, "content": merged})
    return grouped


@app.websocket("/api/ws/{model_id}")
async def websocket_chat(websocket: WebSocket, model_id: str):
    """Process the request"""
    logger.info(f"WebSocket connection established for model: {model_id}")

    client_id = await manager.connect(websocket)
    logger.info(f"Client connected with ID: {client_id}")

    if model_id == "mygpt":
        model = LLMService()
    else:
        model = await ModelFactory.get_model(model_id)
    try:
        # Use context manager instead of manual DB session management
        with get_db_context() as db:
            chat_service = ChatService(db)
            user_service = UserService(db)
            conversation_service = ConversationService(db)
            message_service = MessageService(db)

            # Get or create default user
            user = user_service.get_or_create_default_user()
            stopped = False
            while True:
                # Wait for client messages
                data = await websocket.receive_json()
                command = data.get("command", "")

                if command == "generate":
                    # Start a new generation
                    message = WebSocketChatInput(**data)

                    # Get or create conversation
                    if message.chat_id:
                        conversation = conversation_service.get_conversation(
                            message.chat_id
                        )
                        if not conversation:
                            await websocket.send_json(
                                {"error": "Conversation not found"}
                            )
                            continue
                    else:
                        conversation = conversation_service.create_conversation(
                            user.id, message.message
                        )

                    # Store user message
                    message_service.create_message(
                        content=message.message,
                        role="user",
                        conversation_id=conversation.id,
                    )

                    # Get conversation history for context
                    previous_messages = message_service.get_conversation_messages(
                        conversation.id
                    )

                    # Format the prompt including conversation history
                    previous_messages = [
                        {
                            "role": m.role,
                            "content": m.content,
                        }
                        for m in previous_messages
                    ]
                    # Fixing the Gemma exception:
                    # Conversation roles must alternate user/assistant/user/assistant/
                    if model_id.startswith("gemma"):
                        previous_messages = _fix_gemma_messages(previous_messages)
                    logger.info(f"Previous messages:")
                    print(previous_messages)
                    logging.info(
                        f"Model settings - Temperature: {message.temperature}, Max Length: {message.max_length}, Top P: {message.top_p}"
                    )
                    # Start token generation
                    full_response = ""
                    try:
                        async for token in model.generate_stream(
                            prompt=previous_messages,
                            max_length=message.max_length,
                            temperature=message.temperature,
                            top_p=message.top_p,
                        ):
                            if token.startswith("Error:"):
                                await manager.send_personal_message(
                                    client_id, {"error": token}
                                )
                                break

                            full_response += token
                            await manager.send_personal_message(
                                client_id, {"token": token}
                            )

                            # Check after each token if we should continue
                            # This enables immediate cancellation
                            if await manager.check_for_stop_command(client_id):
                                stopped = True
                                break

                        # Generation completed successfully.
                        # If the generation was stopped, we don't store the response
                        if full_response and not stopped:
                            message_service.create_message(
                                content=full_response,
                                role="assistant",
                                conversation_id=conversation.id,
                            )

                        # Get the updated conversation to include in the response
                        updated_conversation = conversation_service.get_conversation(
                            conversation.id
                        )

                        # Notify client that generation is complete and include conversation data
                        await manager.send_personal_message(
                            client_id,
                            {
                                "status": "complete",
                                "conversation": {
                                    "id": updated_conversation.id,
                                    "title": updated_conversation.title,
                                    "created_at": updated_conversation.created_at.isoformat(),
                                    # "preview": updated_conversation.preview,
                                    "lastMessageTimestamp": updated_conversation.created_at.isoformat(),
                                },
                            },
                        )

                    except Exception as e:
                        logging.error(f"Error during streaming: {str(e)}")
                        await manager.send_personal_message(
                            client_id, {"error": str(e)}
                        )

                elif command == "stop":
                    # Stop command is handled directly during generation
                    pass

                else:
                    await manager.send_personal_message(
                        client_id, {"error": f"Unknown command: {command}"}
                    )
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logging.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        await manager.send_personal_message(client_id, {"error": str(e)})


# @app.websocket("/api/ws/chat")
# async def websocket_chat(websocket: WebSocket):
#     """WebSocket endpoint for chat streaming"""
#     await websocket.accept()

#     try:
#         # Use context manager instead of manual DB session management
#         with get_db_context() as db:
#             chat_service = ChatService(db)
#             user_service = UserService(db)
#             conversation_service = ConversationService(db)
#             message_service = MessageService(db)
#             llm_service = LLMService()

#             # Get or create default user
#             user = user_service.get_or_create_default_user()

#             while True:
#                 # Wait for client messages
#                 data = await websocket.receive_json()
#                 command = data.get("command", "")

#                 if command == "generate":
#                     # Start a new generation
#                     message = WebSocketChatInput(**data)

#                     # Get or create conversation
#                     if message.chat_id:
#                         conversation = conversation_service.get_conversation(
#                             message.chat_id
#                         )
#                         if not conversation:
#                             await websocket.send_json(
#                                 {"error": "Conversation not found"}
#                             )
#                             continue
#                     else:
#                         conversation = conversation_service.create_conversation(
#                             user.id, message.message
#                         )

#                     # Store user message
#                     message_service.create_message(
#                         content=message.message,
#                         role="user",
#                         conversation_id=conversation.id,
#                     )

#                     # Get conversation history for context
#                     previous_messages = message_service.get_conversation_messages(
#                         conversation.id
#                     )

#                     # Format the prompt including conversation history
#                     formatted_prompt = chat_service._format_conversation_for_model(
#                         previous_messages
#                     )
#                     logging.info(f"Formatted prompt: {formatted_prompt}")
#                     logging.info(
#                         f"Model settings - Temperature: {message.temperature}, Max Length: {message.max_length}, Top P: {message.top_p}"
#                     )
#                     # Start token generation
#                     full_response = ""

#                     try:
#                         async for token in llm_service.generate_stream(
#                             prompt=formatted_prompt,
#                             max_length=message.max_length,
#                             temperature=message.temperature,
#                             top_p=message.top_p,
#                         ):
#                             if token.startswith("Error:"):
#                                 await websocket.send_json({"error": token})
#                                 break

#                             full_response += token
#                             await websocket.send_json({"token": token})

#                             # Check after each token if we should continue
#                             # This enables immediate cancellation
#                             try:
#                                 # Non-blocking check for a stop message with a very short timeout
#                                 data = await asyncio.wait_for(
#                                     websocket.receive_json(), timeout=0.001
#                                 )
#                                 if data.get("command") == "stop":
#                                     logging.info("Generation stopped by client request")
#                                     break
#                             except asyncio.TimeoutError:
#                                 # No message received, continue generation
#                                 pass

#                         # Generation completed successfully
#                         # Store the assistant's response in the database
#                         if full_response:
#                             message_service.create_message(
#                                 content=full_response,
#                                 role="assistant",
#                                 conversation_id=conversation.id,
#                             )

#                         # Get the updated conversation to include in the response
#                         updated_conversation = conversation_service.get_conversation(
#                             conversation.id
#                         )

#                         # Notify client that generation is complete and include conversation data
#                         await websocket.send_json(
#                             {
#                                 "status": "complete",
#                                 "conversation": {
#                                     "id": updated_conversation.id,
#                                     "title": updated_conversation.title,
#                                     "created_at": updated_conversation.created_at.isoformat(),
#                                     # "preview": updated_conversation.preview,
#                                     "lastMessageTimestamp": updated_conversation.created_at.isoformat(),
#                                 },
#                             }
#                         )

#                     except Exception as e:
#                         logging.error(f"Error during streaming: {str(e)}")
#                         await websocket.send_json({"error": str(e)})

#                 elif command == "stop":
#                     # Stop command is handled directly during generation
#                     pass

#                 else:
#                     await websocket.send_json({"error": f"Unknown command: {command}"})

#     except WebSocketDisconnect:
#         logging.info("WebSocket client disconnected")

#     except Exception as e:
#         logging.error(f"WebSocket error: {str(e)}")
#         await websocket.send_json({"error": str(e)})
