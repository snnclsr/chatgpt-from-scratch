from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class ChatInput(BaseModel):
    message: str = Field(..., min_length=1, description="The message sent by the user")
    chat_id: Optional[int] = Field(
        None, description="The ID of the existing conversation"
    )
    image_url: Optional[str] = Field(
        None, description="URL or path to an uploaded image"
    )


class StreamingChatInput(ChatInput):
    max_length: Optional[int] = Field(
        20, description="Maximum number of tokens to generate"
    )
    temperature: Optional[float] = Field(
        0.7, description="Sampling temperature (0.0-1.0)"
    )
    top_p: Optional[float] = Field(
        0.9, description="Nucleus sampling parameter (0.0-1.0)"
    )


class WebSocketChatInput(StreamingChatInput):
    command: Literal["generate", "stop"] = Field(
        "generate", description="Command to execute (generate or stop)"
    )


class WebSocketVisionChatInput(WebSocketChatInput):
    image_url: str = Field(..., description="URL or path to the uploaded image")


class MessageResponse(BaseModel):
    id: str
    content: str
    role: str
    timestamp: datetime
    image_url: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    preview: Optional[str] = None


class ChatResponse(BaseModel):
    response: str = Field(..., description="The response from the assistant")
    message_id: int = Field(..., description="The ID of the assistant's message")
    conversation: ConversationResponse = Field(..., description="The conversation data")


class ImageUploadResponse(BaseModel):
    success: bool
    message: str
    image_url: Optional[str] = None
    conversation_id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
