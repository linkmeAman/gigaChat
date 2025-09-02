from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import pyotp
import json

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime(timezone=True))
    lockout_until = Column(DateTime(timezone=True))
    role = Column(String(50), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 2FA fields
    totp_secret = Column(String(32))
    totp_enabled = Column(Boolean, default=False)
    backup_codes = Column(JSON)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    webauthn_credentials = relationship("WebAuthnCredential", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")

    def generate_totp_secret(self):
        """Generate a new TOTP secret for the user."""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret

    def verify_totp(self, code: str) -> bool:
        """Verify a TOTP code."""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)

    def generate_backup_codes(self, n=10):
        """Generate backup codes for 2FA recovery."""
        import secrets
        codes = [secrets.token_hex(4) for _ in range(n)]
        self.backup_codes = json.dumps(codes)
        return codes

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    refresh_token = Column(String(255), unique=True, index=True)
    device_id = Column(String(255))
    device_info = Column(JSON)
    ip_address = Column(String(45))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Relationship
    user = relationship("User", back_populates="sessions")

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    credential_id = Column(String(255), unique=True, index=True)
    public_key = Column(String(512))
    sign_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="webauthn_credentials")

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String(50))  # "github", "google"
    account_id = Column(String(255))
    account_email = Column(String(255))
    access_token = Column(String(512))
    refresh_token = Column(String(512))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="oauth_accounts")