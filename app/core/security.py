import os
import bcrypt
import pyseto
import hashlib
import requests
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, cast
import json
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.auth import User, Session as UserSession
from app.core.database import get_db
import re

def get_password_hash(password: str) -> str:
    """Generate a secure password hash using bcrypt with pepper."""
    # Add pepper to password before hashing
    peppered = f"{password}{settings.AUTH_PASSWORD_PEPPER}"
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_WORK_FACTOR)
    return bcrypt.hashpw(peppered.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    peppered = f"{plain_password}{settings.AUTH_PASSWORD_PEPPER}"
    return bcrypt.checkpw(peppered.encode(), hashed_password.encode())

def is_password_breached(password: str) -> bool:
    """Check if password appears in HIBP database using k-anonymity."""
    if not settings.HIBP_API_KEY:
        return False
    
    # Get first 5 chars of password hash
    password_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    hash_prefix = password_hash[:5]
    
    # Query HIBP API
    headers = {"hibp-api-key": settings.HIBP_API_KEY.get_secret_value()}
    response = requests.get(
        f"https://api.pwnedpasswords.com/range/{hash_prefix}",
        headers=headers
    )
    
    if response.status_code != 200:
        return False
    
    # Check if hash suffix appears in response
    hash_suffix = password_hash[5:]
    return hash_suffix in response.text

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password against security policy."""
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"
    
    checks = [
        (r"[A-Z]", "uppercase letter"),
        (r"[a-z]", "lowercase letter"),
        (r"[0-9]", "number"),
        (r"[^A-Za-z0-9]", "special character")
    ]
    
    missing = [desc for pattern, desc in checks if not re.search(pattern, password)]
    if missing:
        return False, f"Password must contain at least one {', '.join(missing)}"
    
    if is_password_breached(password):
        return False, "This password has appeared in data breaches. Please choose a different one."
    
    return True, "Password meets security requirements"

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a Paseto token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire.timestamp(),  # Convert to unix timestamp
        "iss": settings.PASETO_ISSUER,
        "aud": settings.PASETO_AUDIENCE,
        "iat": datetime.now(UTC).timestamp()  # Convert to unix timestamp
    })

    # Get bytes for the key
    secret_bytes = settings.PASETO_SECRET.encode() if isinstance(settings.PASETO_SECRET, str) else settings.PASETO_SECRET
    key = pyseto.Key.new(
        version=2,
        purpose="local",
        key=secret_bytes
    )

    token = pyseto.encode(
        key,
        payload=to_encode
    )
    
    return token.decode()

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a Paseto token."""
    try:
        # Get bytes for the key
        secret_bytes = settings.PASETO_SECRET.encode() if isinstance(settings.PASETO_SECRET, str) else settings.PASETO_SECRET
        key = pyseto.Key.new(
            version=2,
            purpose="local",
            key=secret_bytes
        )
        
        # Add clock leeway for token validation
        now = datetime.now(UTC).timestamp()  # Convert to timestamp
        leeway = settings.PASETO_LEEWAY_SECONDS
        
        token_obj = pyseto.decode(
            key,
            token.encode()
        )
        
        # Convert payload to string if it's bytes
        payload_str = token_obj.payload.decode() if isinstance(token_obj.payload, bytes) else str(token_obj.payload)
        payload = cast(Dict[str, Any], json.loads(payload_str))
        
        # Verify expiration with leeway (using timestamps)
        exp = payload["exp"]
        if exp - leeway <= now:
            return None
            
        # Verify issuer and audience
        if payload.get("iss") != settings.PASETO_ISSUER:
            return None
        if payload.get("aud") != settings.PASETO_AUDIENCE:
            return None
            
        return payload
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current authenticated user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    email = payload["sub"]
    if not email:
        raise credentials_exception

    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    
    if not bool(user.is_active):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )

    return user

def create_session(
    db: Session,
    user: User,
    device_id: Optional[str] = None,
    device_info: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> UserSession:
    """Create a new session for the user."""
    session = UserSession(
        user_id=user.id,
        device_id=device_id or "",
        device_info=json.dumps(device_info or {}),
        ip_address=ip_address or "127.0.0.1",
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session