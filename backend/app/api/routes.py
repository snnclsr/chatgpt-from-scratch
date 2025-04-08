from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from ..schemas import ImageUploadResponse
from ..utils.image_utils import save_uploaded_image
from ..database import get_db_context
from ..services.user_service import UserService
from ..services.conversation_service import ConversationService

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Welcome to AI Chat API"}


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    conversation_id: Optional[int] = Form(None),
    # db: Session = Depends(get_db_context),
):
    """
    Upload an image for use with a vision model
    """
    try:
        with get_db_context() as db:
            # Read the file content
            file_content = await file.read()

            # Process and save the image
            success, message, file_path = save_uploaded_image(
                file_content, file.filename
            )

            if not success:
                raise HTTPException(status_code=400, detail=message)

            # Create the relative URL
            file_url = os.path.basename(file_path)

            # Get user
            user_service = UserService(db)
            user = user_service.get_or_create_default_user()

            # If no conversation_id is provided, create a new vision conversation
            if not conversation_id:
                conversation_service = ConversationService(db)
                conversation = conversation_service.create_conversation(
                    title="Vision Chat", user_id=user.id
                )
                conversation_id = conversation.id

            return ImageUploadResponse(
                success=True,
                message="Image uploaded successfully",
                image_url=file_url,
                conversation_id=conversation_id,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
