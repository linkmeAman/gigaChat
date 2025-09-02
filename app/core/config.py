from pydantic import BaseSettings, validator, SecretStr
from typing import Optional, List
import secrets
from datetime import timedelta

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "GigaChat"
    VERSION: str = "1.3.0-free"
    DESCRIPTION: str = "A free and open-source ChatGPT-like conversational web app"
    
    # Security
    AUTH_PASSWORD_PEPPER: str = secrets.token_urlsafe(32)
    PASETO_SECRET: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASETO_ISSUER: str = "GigaChat"
    PASETO_AUDIENCE: str = "GigaChat-Web"
    PASETO_LEEWAY_SECONDS: int = 60
    BCRYPT_WORK_FACTOR: int = 12
    
    # Authentication
    ACCOUNT_LOCKOUT_THRESHOLD: int = 5
    ACCOUNT_LOCKOUT_WINDOW_MINUTES: int = 15
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    MIN_PASSWORD_LENGTH: int = 12
    MAX_CONCURRENT_SESSIONS: int = 10
    TOTP_ISSUER: str = "GigaChat"
    HIBP_API_KEY: Optional[SecretStr] = None
    
    # Database
    DATABASE_URL: str = "mysql://root:password@localhost/gigachat"
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 50
    DB_POOL_TIMEOUT_SECONDS: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SECONDS: int = 120
    
    # File Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: SecretStr
    MINIO_SECRET_KEY: SecretStr
    MINIO_BUCKET: str = "gigachat"
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_FILE_TYPES: List[str] = ["txt", "pdf", "md", "png", "jpg", "csv", "json"]
    
    # AI Model Settings
    DEFAULT_MODEL: str = "mistral-7b-instruct"  # Free and open-source model
    MODEL_SERVER: str = "vllm"  # or "tgi" or "llama.cpp"
    DEVICE: str = "cuda"  # or "cpu"
    MAX_TOKENS: int = 1024
    MAX_CONTEXT_WINDOW: int = 4096
    TEMPERATURE: float = 0.7
    TOP_P: float = 0.9
    
    # Vector Store
    VECTOR_STORE: str = "faiss"  # or "qdrant"
    EMBEDDING_MODEL: str = "bge-small-en-v1.5"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    
    # Rate Limiting
    PUBLIC_RATE_LIMIT: int = 60  # requests per minute
    AUTH_RATE_LIMIT: int = 120  # requests per minute
    RATE_LIMIT_BURST: int = 30
    
    # Observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_RETENTION_DAYS: int = 7
    TRACE_SAMPLE_RATE: float = 0.2
    
    # Search
    SEARXNG_URL: Optional[str] = "http://localhost:8888"
    SEARCH_TIMEOUT_MS: int = 8000
    SEARCH_CACHE_SECONDS: int = 300
    
    # Security Headers
    CSP_POLICY: str = "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https:"
    HSTS_MAX_AGE: int = 31536000
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def validate_file_types(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()