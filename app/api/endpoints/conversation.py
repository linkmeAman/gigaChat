from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import csv
import markdown
from weasyprint import HTML
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.authorization import RBACPolicy, Resource, Action
from app.models.auth import User
from app.models.conversation import (
    Conversation,
    Message,
    ConversationFeedback,
    MessageFeedback
)

router = APIRouter()

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with its messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    title: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    retention_days: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation details."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if title:
        conversation.title = title
    if is_pinned is not None:
        conversation.is_pinned = is_pinned
    if tags:
        conversation.tags = tags
    if retention_days:
        conversation.retention_days = retention_days
    
    db.commit()
    db.refresh(conversation)
    return conversation

@router.post("/conversations/{conversation_id}/feedback")
async def add_conversation_feedback(
    conversation_id: int,
    rating: int,
    comment: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add feedback to a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    feedback = ConversationFeedback(
        conversation_id=conversation_id,
        user_id=user.id,
        rating=rating,
        comment=comment
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

@router.post("/messages/{message_id}/feedback")
async def add_message_feedback(
    message_id: int,
    thumbs_up: Optional[bool] = None,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add feedback to a message."""
    message = db.query(Message).join(Conversation).filter(
        Message.id == message_id,
        Conversation.user_id == user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    feedback = MessageFeedback(
        message_id=message_id,
        user_id=user.id,
        thumbs_up=thumbs_up,
        rating=rating,
        comment=comment
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

@router.get("/conversations/export/{conversation_id}")
async def export_conversation(
    conversation_id: int,
    format: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export conversation in various formats."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    # Prepare export path
    filename = f"conversation_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == "json":
        data = {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                    } for msg in messages
                ]
            }
        }
        export_path = f"exports/{filename}.json"
        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    elif format == "csv":
        export_path = f"exports/{filename}.csv"
        with open(export_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Role", "Content"])
            for msg in messages:
                writer.writerow([
                    msg.created_at.isoformat(),
                    msg.role,
                    msg.content
                ])
                
    elif format == "markdown":
        export_path = f"exports/{filename}.md"
        with open(export_path, 'w') as f:
            f.write(f"# {conversation.title}\n\n")
            for msg in messages:
                f.write(f"## {msg.role.title()} - {msg.created_at.isoformat()}\n\n")
                f.write(f"{msg.content}\n\n")
                
    elif format == "pdf":
        # Convert to HTML first
        html_content = f"<h1>{conversation.title}</h1>"
        for msg in messages:
            html_content += f"<h2>{msg.role.title()} - {msg.created_at.isoformat()}</h2>"
            html_content += f"<p>{msg.content}</p>"
        
        export_path = f"exports/{filename}.pdf"
        HTML(string=html_content).write_pdf(export_path)
        
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    # Clean up old exports in background
    background_tasks.add_task(cleanup_old_exports)
    
    return FileResponse(
        export_path,
        media_type=f"application/{format}",
        filename=f"{filename}.{format}"
    )

async def cleanup_old_exports():
    """Clean up export files older than 24 hours."""
    import os
    import glob
    from datetime import datetime, timedelta
    
    cleanup_before = datetime.now() - timedelta(hours=24)
    
    for file in glob.glob("exports/*.*"):
        if datetime.fromtimestamp(os.path.getctime(file)) < cleanup_before:
            os.remove(file)