from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from .moderation import moderator
from .auth import get_current_user
from .models import User

router = APIRouter()

class TextModerationRequest(BaseModel):
    text: str

class TextModerationResponse(BaseModel):
    is_safe: bool
    issues: List[str]

class FileModerationResponse(BaseModel):
    is_safe: bool
    reason: str = None

@router.post("/moderate/text", response_model=TextModerationResponse)
async def moderate_text(
    request: TextModerationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Moderate text content for toxicity, profanity, and sensitive information.
    """
    is_safe, issues = await moderator.moderate_text(request.text)
    return TextModerationResponse(is_safe=is_safe, issues=issues)

@router.post("/moderate/file", response_model=FileModerationResponse)
async def moderate_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Scan uploaded file for malware and other threats.
    """
    is_safe, reason = await moderator.moderate_file(file)
    return FileModerationResponse(is_safe=is_safe, reason=reason)