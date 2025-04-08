import uuid
import logging
from itertools import groupby
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import os

import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.routes import router
from app.database import SessionLocal, engine, get_db_context
from app import models
from app.schemas import (
    ConversationResponse,
    HealthResponse,
    WebSocketChatInput,
    WebSocketVisionChatInput,
)
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.user_service import UserService
from app.services.llm_service import LLMService
# from routes.router import router as ws_router

from ml.factory import ModelFactory
from ml.config import MODEL_CONFIGS
from app.utils.image_utils import UPLOADS_DIR, ensure_upload_dir

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Ensure the uploads directory exists
ensure_upload_dir()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all models from config
    for model_id, config in MODEL_CONFIGS.items():
        logger.info(f"Registering model: {model_id}")
        await ModelFactory.get_model(model_id)
        # ModelFactory.register_model(model_id, config)

    yield

    # Clean up
    for model_id in MODEL_CONFIGS.keys():
        await ModelFactory.unload_model(model_id)


app = FastAPI(title="AI Chat System", lifespan=lifespan)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register routes
app.include_router(router, prefix="/api")

# Mount the uploads directory for static file access
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
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
            # chat_service = ChatService(db)
            user_service = UserService(db)
            conversation_service = ConversationService(db)
            message_service = MessageService(db)

            # Get or create default user
            user = user_service.get_or_create_default_user()
            stopped = False
            while True:
                # data = await manager.receive_message(client_id)
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
                            await manager.send_personal_message(
                                client_id, {"error": "Conversation not found"}
                            )
                            continue
                    else:
                        # Title summarizer with Qwen
                        title = ""
                        title_messages = [
                            {
                                "role": "system",
                                "content": """You are a helpful assistant that summarizes conversations in less than 30 characters.""",
                            },
                            {
                                "role": "user",
                                "content": message.message,
                            },
                        ]
                        async for token in model.generate_stream(
                            prompt=title_messages,
                            # max_length=250,
                            max_new_tokens=40,
                            temperature=0.3,
                        ):
                            title += token
                        logger.info(f"Generated title: {title}")
                        # First message, create a new conversation
                        # title = message.message[:35]
                        conversation = conversation_service.create_conversation(
                            user.id, title
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
                            # max_length=message.max_length,
                            max_new_tokens=message.max_length,
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


@app.websocket("/api/ws/vision/{model_id}")
async def websocket_vision_chat(websocket: WebSocket, model_id: str):
    """Handle vision model interactions"""
    logger.info(f"Vision WebSocket connection established for model: {model_id}")

    client_id = await manager.connect(websocket)
    logger.info(f"Vision client connected with ID: {client_id}")

    # Check if model supports vision
    is_vision_model = ModelFactory.is_vision_model(model_id)
    print(f"Is vision model: {is_vision_model}")
    if not is_vision_model:
        await manager.send_personal_message(
            client_id,
            {
                "type": "error",
                "message": f"Model {model_id} does not support vision capabilities",
            },
        )
        manager.disconnect(client_id)
        return

    # Get the vision model
    model = await ModelFactory.get_model(model_id)
    print(f"Vision model: {model}")
    print(f"Model ID: {model_id}")
    print("Starting vision chat...")

    async def fake_token_stream(tokens):
        for token in tokens:
            yield token
            await asyncio.sleep(0)  # Simulate async behavior

    try:
        with get_db_context() as db:
            user_service = UserService(db)
            conversation_service = ConversationService(db)
            message_service = MessageService(db)

            # Get or create default user
            user = user_service.get_or_create_default_user()
            stopped = False

            while not stopped:
                try:
                    # Wait for a message from the client
                    data = await websocket.receive_json()

                    # Parse the user's message with image
                    request = WebSocketVisionChatInput(**data)

                    if request.command == "stop":
                        logger.info(
                            f"Received stop command from vision client: {client_id}"
                        )
                        stopped = True
                        break

                    # Get or create conversation
                    if request.chat_id:
                        conversation = conversation_service.get_conversation(
                            request.chat_id
                        )
                        if not conversation:
                            raise HTTPException(
                                status_code=404, detail="Conversation not found"
                            )
                    else:
                        # Create a new vision conversation
                        conversation = conversation_service.create_conversation(
                            title="Vision Chat",
                            user_id=user.id,
                        )

                    # Get full image path
                    image_path = os.path.join(UPLOADS_DIR, request.image_url)
                    if not os.path.exists(image_path):
                        raise FileNotFoundError(f"Image not found: {image_path}")

                    # Save user message to database with image URL
                    user_message = message_service.create_message(
                        content=request.message,
                        role="user",
                        conversation_id=conversation.id,
                        image_url=request.image_url,
                    )

                    # # Create an empty assistant message that we'll update as tokens come in
                    # assistant_message = message_service.create_message(
                    #     content="",  # Empty content to start
                    #     role="assistant",
                    #     conversation_id=conversation.id,
                    # )

                    # # Send initial message to acknowledge we're processing
                    # await manager.send_personal_message(
                    #     client_id,
                    #     {
                    #         "type": "start",
                    #         "message_id": assistant_message.id,
                    #         "conversation_id": conversation.id,
                    #     },
                    # )

                    # Stream the response using image and prompt
                    full_response = ""
                    print("Generating response...")
                    # Fake response for now.
                    # tokens = [
                    #     "Hello ",
                    #     "world ",
                    #     "!",
                    #     "This ",
                    #     "is ",
                    #     "a ",
                    #     "test",
                    #     "This ",
                    #     "is ",
                    #     "a ",
                    #     "test",
                    # ]
                    # async for token in fake_token_stream(tokens):
                    #     if token.startswith("Error:"):
                    #         await manager.send_personal_message(
                    #             client_id, {"error": token}
                    #         )
                    #         break

                    #     full_response += token
                    #     await manager.send_personal_message(client_id, {"token": token})

                    #     # Check after each token if we should continue
                    #     # This enables immediate cancellation
                    #     if await manager.check_for_stop_command(client_id):
                    #         stopped = True
                    #         break

                    async for token in model.generate_stream_with_image(
                        request.message, image_path
                    ):
                        full_response += token

                        # Check for stop command
                        if await manager.check_for_stop_command(client_id):
                            logger.info("Vision generation stopped by client request")
                            stopped = True
                            break

                        # Send token to the client
                        await manager.send_personal_message(
                            client_id,
                            {
                                "type": "token",
                                "token": token,
                                # "message_id": assistant_message.id,
                            },
                        )

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

                except WebSocketDisconnect:
                    logger.info(f"Vision client disconnected: {client_id}")
                    stopped = True
                    break
                except Exception as e:
                    logger.error(f"Error processing vision request: {str(e)}")
                    # Try to send error to client
                    try:
                        await manager.send_personal_message(
                            client_id, {"type": "error", "message": str(e)}
                        )
                    except:
                        pass

        # Clean up
        manager.disconnect(client_id)
        logger.info(f"Vision client connection closed: {client_id}")

    except Exception as e:
        logger.error(f"Vision WebSocket error: {str(e)}")
        # Try to send error to client
        try:
            await manager.send_personal_message(
                client_id, {"type": "error", "message": str(e)}
            )
        except:
            pass
        manager.disconnect(client_id)
