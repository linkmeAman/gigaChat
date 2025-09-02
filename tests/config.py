"""Test configuration module."""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class TestSettings(BaseSettings):
    """Test settings configuration."""
    
    # Test Database
    DATABASE_URL: str = "sqlite:///./test.db"
    TEST_DB: bool = True
    
    # Test User
    TEST_USER_EMAIL: str = "test@example.com"
    TEST_USER_PASSWORD: str = "Test123!@#"
    TEST_USER_NAME: str = "Test User"
    
    # Test Security
    TEST_PASETO_SECRET: str = "12345678901234567890123456789012"  # 32 bytes
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env.test"
        env_file_encoding = "utf-8"

test_settings = TestSettings()