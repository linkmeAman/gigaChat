from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.i18n import i18n
from app.core.security import get_current_user
from app.models.auth import User
from typing import List, Dict

router = APIRouter()

@router.get("/i18n/languages")
async def get_supported_languages() -> List[str]:
    """Get list of supported languages."""
    return i18n.supported_languages

@router.get("/i18n/translations/{language}")
async def get_translations(
    language: str,
    user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Get translations for a specific language."""
    if language not in i18n.supported_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Language {language} is not supported"
        )
    return i18n.translations.get(language, {})

@router.get("/i18n/missing/{language}")
async def get_missing_translations(
    language: str,
    user: User = Depends(get_current_user)
) -> List[str]:
    """Get list of keys missing translations for a language."""
    return i18n.get_missing_translations(language)

@router.post("/i18n/{language}/{key}")
async def add_translation(
    language: str,
    key: str,
    text: str,
    user: User = Depends(get_current_user)
):
    """Add or update a translation."""
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can add translations"
        )
    i18n.add_translation(language, key, text)
    return {"message": "Translation added successfully"}