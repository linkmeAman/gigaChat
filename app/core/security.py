import bcrypt
import pyseto
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.auth import User, Session as UserSession
import json
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

def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None) -> str:
    """Create a Paseto token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iss": settings.PASETO_ISSUER,
        "aud": settings.PASETO_AUDIENCE,
        "iat": datetime.utcnow()
    })
    
    key = pyseto.Key.new(
        version=2,
        purpose="local",
        key=settings.PASETO_SECRET.encode()
    )
    
    token = pyseto.encode(
        key,
        payload=to_encode,
        serializer=pyseto.JsonSerializer()
    )
    
    return token.decode()

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a Paseto token."""
    try:
        key = pyseto.Key.new(
            version=2,
            purpose="local",
            key=settings.PASETO_SECRET.encode()
        )
        
        # Add clock leeway for token validation
        now = datetime.utcnow()
        leeway = timedelta(seconds=settings.PASETO_LEEWAY_SECONDS)
        
        payload = pyseto.decode(
            key,
            token.encode(),
            serializer=pyseto.JsonSerializer()
        )
        
        # Verify expiration with leeway
        exp = datetime.fromtimestamp(payload["exp"])
        if exp - leeway <= now:
            return None
            
        # Verify issuer and audience
        if payload.get("iss") != settings.PASETO_ISSUER:
            return None
        if payload.get("aud") != settings.PASETO_AUDIENCE:
            return None
            
        return payload
    except:
        return None

def check_account_lockout(user: User) -> bool:
    """Check if account is locked and handle lockout expiry."""
    if not user.is_locked:
        return False
        
    if user.lockout_until and datetime.utcnow() > user.lockout_until:
        # Lockout period expired, reset lockout
        user.is_locked = False
        user.failed_login_attempts = 0
        user.lockout_until = None
        return False
        
    return True

def handle_failed_login(db: Session, user: User):
    """Handle failed login attempt and implement account lockout."""
    now = datetime.utcnow()
    
    # Reset failed attempts if window expired
    if user.last_failed_login:
        window_start = now - timedelta(minutes=settings.ACCOUNT_LOCKOUT_WINDOW_MINUTES)
        if user.last_failed_login < window_start:
            user.failed_login_attempts = 0
    
    # Increment failed attempts
    user.failed_login_attempts += 1
    user.last_failed_login = now
    
    # Check if should lock account
    if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
        user.is_locked = True
        user.lockout_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
    
    db.commit()

def create_session(
    db: Session,
    user: User,
    device_id: str,
    device_info: dict,
    ip_address: str
) -> UserSession:
    """Create a new session for the user."""
    # Check concurrent session limit
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True
    ).count()
    
    if active_sessions >= settings.MAX_CONCURRENT_SESSIONS:
        # Remove oldest session
        oldest_session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_active == True
        ).order_by(UserSession.created_at).first()
        
        oldest_session.is_active = False
        db.commit()
    
    # Create new session
    session = UserSession(
        user_id=user.id,
        device_id=device_id,
        device_info=json.dumps(device_info),
        ip_address=ip_address,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session