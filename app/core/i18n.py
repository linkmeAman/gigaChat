from typing import Dict, List, Optional
import json
import os
from fastapi import HTTPException
from pydantic import BaseModel

class Translation(BaseModel):
    language: str
    messages: Dict[str, str]

class I18nManager:
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "es", "fr"]
        self.load_translations()

    def load_translations(self):
        """Load translations from JSON files."""
        translations_dir = "app/i18n"
        for lang in self.supported_languages:
            try:
                with open(f"{translations_dir}/{lang}.json", "r", encoding="utf-8") as f:
                    self.translations[lang] = json.load(f)
            except FileNotFoundError:
                # Create empty translation file if it doesn't exist
                self.translations[lang] = {}
                os.makedirs(translations_dir, exist_ok=True)
                with open(f"{translations_dir}/{lang}.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)

    def get_text(self, key: str, language: str = None) -> str:
        """Get translated text for a given key and language."""
        lang = language or self.default_language
        if lang not in self.supported_languages:
            lang = self.default_language

        return self.translations.get(lang, {}).get(key, key)

    def add_translation(self, language: str, key: str, text: str):
        """Add or update a translation."""
        if language not in self.supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Language {language} is not supported"
            )

        if language not in self.translations:
            self.translations[language] = {}

        self.translations[language][key] = text
        
        # Save to file
        with open(f"app/i18n/{language}.json", "w", encoding="utf-8") as f:
            json.dump(self.translations[language], f, ensure_ascii=False, indent=2)

    def get_missing_translations(self, language: str) -> List[str]:
        """Get list of keys missing translations for a language."""
        if language not in self.supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Language {language} is not supported"
            )

        en_keys = set(self.translations.get("en", {}).keys())
        lang_keys = set(self.translations.get(language, {}).keys())
        return list(en_keys - lang_keys)

# Initialize global i18n manager
i18n = I18nManager()