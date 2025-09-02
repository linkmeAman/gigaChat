from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import User, Conversation, Message, Feedback
from app.core.ai import get_ai_response
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class MessageCreate(BaseModel):
    content: str
    conversation_id: int = None

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

@router.post("/send", response_model=List[MessageResponse])
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create or get conversation
    if message.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == message.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(user_id=current_user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Store user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=message.content
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Get AI response
    ai_content = await get_ai_response(message.content)
    
    # Store AI message
    ai_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_content
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return [
        MessageResponse.from_orm(user_message),
        MessageResponse.from_orm(ai_message)
    ]

@router.post("/{message_id}/feedback")
async def give_feedback(
    message_id: int,
    rating: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate message exists
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Create or update feedback
    feedback = db.query(Feedback).filter(
        Feedback.user_id == current_user.id,
        Feedback.message_id == message_id
    ).first()

    if feedback:
        feedback.rating = rating
    else:
        feedback = Feedback(
            user_id=current_user.id,
            message_id=message_id,
            rating=rating
        )
        db.add(feedback)

    db.commit()
    return {"status": "success"}