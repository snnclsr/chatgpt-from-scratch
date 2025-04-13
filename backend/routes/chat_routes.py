from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..schemas import ConversationResponse
from ..database import get_db
from ..services.message_service import MessageService
from ..services.conversation_service import ConversationService
from ..services.user_service import UserService


router = APIRouter(
    # prefix="/",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)


@router.get("/api/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: int, db: Session = Depends(get_db)):
    """Get all messages for a specific chat"""
    try:
        message_service = MessageService(db)
        messages = message_service.get_conversation_messages(chat_id)
        return message_service.format_messages_for_response(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/conversations", response_model=List[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    """Get all conversations for the current user"""
    try:
        user_service = UserService(db)
        conversation_service = ConversationService(db)

        user = user_service.get_or_create_default_user()
        return conversation_service.get_user_conversations(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a specific conversation"""
    try:
        conversation_service = ConversationService(db)
        if conversation_service.delete_conversation(conversation_id):
            return {"status": "success", "message": "Conversation deleted successfully"}
        raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
