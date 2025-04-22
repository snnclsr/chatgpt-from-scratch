import os
import logging
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from .connection import manager
from ...services.user_service import UserService
from ...services.conversation_service import ConversationService
from ...services.message_service import MessageService
from ...database import get_db_context
from ...schemas import WebSocketVisionChatInput
from ...ml.factory import ModelFactory
from ...utils.image_utils import UPLOADS_DIR

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/api/ws/vision/{model_id}")
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

    # For testing, we can fake the token stream (faster while developing).
    async def fake_token_stream(tokens):
        for token in tokens:
            yield token
            await asyncio.sleep(0.05)  # 1/20 = 0.05 seconds for 20 tokens per second

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
                    print(f"Vision request: {request}")

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
