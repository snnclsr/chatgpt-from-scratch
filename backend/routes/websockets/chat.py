import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .connection import manager
from ...services.llm_service import LLMService
from ...services.user_service import UserService
from ...services.conversation_service import ConversationService
from ...services.message_service import MessageService
from ...database import get_db_context
from ...schemas import WebSocketChatInput
from ...ml.factory import ModelFactory
from ...utils.message_utils import fix_gemma_messages

router = APIRouter()

logger = logging.getLogger(__name__)


@router.websocket("/api/ws/{model_id}")
async def websocket_chat(websocket: WebSocket, model_id: str):
    """Process the request"""
    logger.info(f"WebSocket connection established for model: {model_id}")

    client_id = await manager.connect(websocket)
    logger.info(f"Client connected with ID: {client_id}")

    try:
        model = await ModelFactory.get_model(model_id)
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        await manager.send_personal_message(client_id, {"error": str(e)})
        return

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
                        # title_messages = [
                        #     {
                        #         "role": "system",
                        #         "content": """You are a helpful assistant that summarizes conversations in less than 30 characters.""",
                        #     },
                        #     {
                        #         "role": "user",
                        #         "content": message.message,
                        #     },
                        # ]
                        # async for token in model.generate_stream(
                        #     prompt=title_messages,
                        #     # max_length=250,
                        #     max_new_tokens=40,
                        #     temperature=0.3,
                        # ):
                        #     title += token
                        title = message.message[:35]
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
                        previous_messages = fix_gemma_messages(previous_messages)
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
