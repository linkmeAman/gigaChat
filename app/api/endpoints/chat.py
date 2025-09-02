from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.authorization import RBACPolicy, Resource, Action
from app.models.auth import User
from app.models.conversation import Conversation, Message
from app.core.database import get_db
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.get("/chat", response_class=HTMLResponse)
async def get_chat_page(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Render the main chat interface."""
    return templates.TemplateResponse(
        "chat.html",
        {"request": {}, "user": user}
    )

@router.get("/conversations")
async def get_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the list of user's conversations."""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).order_by(Conversation.updated_at.desc()).all()
    
    return templates.TemplateResponse(
        "conversation_list.html",
        {"request": {}, "conversations": conversations}
    )

@router.post("/conversations/new")
async def create_conversation(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    conversation = Conversation(user_id=user.id, title="New Chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return templates.TemplateResponse(
        "conversation_item.html",
        {"request": {}, "conversation": conversation}
    )

@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a conversation."""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    return templates.TemplateResponse(
        "message_list.html",
        {"request": {}, "messages": messages}
    )

@router.post("/messages")
async def create_message(
    content: str,
    conversation_id: int,
    attachment: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new message in a conversation."""
    # Check permissions
    rbac = RBACPolicy(db)
    if not rbac.check_permission(user, Resource.MESSAGE, Action.CREATE):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Handle file upload if present
    attachment_path = None
    if attachment:
        from app.core.files import save_file
        attachment_path = await save_file(attachment)
    
    # Create message
    message = Message(
        conversation_id=conversation_id,
        user_id=user.id,
        content=content,
        attachment_path=attachment_path
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Broadcast to WebSocket connections
    await manager.broadcast(json.dumps({
        "type": "message",
        "html": templates.get_template("message.html").render(
            {"message": message}
        )
    }))
    
    return templates.TemplateResponse(
        "message.html",
        {"request": {}, "message": message}
    )

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user)
):
    """Handle WebSocket connections for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)