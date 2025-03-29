from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ChatInput(BaseModel):
    message: str = Field(..., min_length=1, description="The message sent by the user")
    chat_id: Optional[int] = Field(
        None, description="The ID of the existing conversation"
    )


class StreamingChatInput(ChatInput):
    max_length: Optional[int] = Field(
        200, description="Maximum number of tokens to generate"
    )
    temperature: Optional[float] = Field(
        0.7, description="Sampling temperature (0.0-1.0)"
    )
    top_p: Optional[float] = Field(
        0.9, description="Nucleus sampling parameter (0.0-1.0)"
    )


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    preview: Optional[str] = None


class ChatResponse(BaseModel):
    response: str = Field(..., description="The response from the assistant")
    message_id: int = Field(..., description="The ID of the assistant's message")
    conversation: ConversationResponse = Field(..., description="The conversation data")


class HealthResponse(BaseModel):
    status: str
