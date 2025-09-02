from authlib.integrations.starlette_client import OAuth
from app.core.config import settings
from app.models.auth import User, OAuthAccount
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Initialize OAuth
oauth = OAuth()

# Configure GitHub
oauth.register(
    name='github',
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Configure Google
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

async def handle_oauth_callback(
    provider: str,
    code: str,
    db: Session
) -> Tuple[Optional[User], Optional[str]]:
    """Handle OAuth callback and create/update user."""
    try:
        if provider == "github":
            user_data = await handle_github_callback(code)
        elif provider == "google":
            user_data = await handle_google_callback(code)
        else:
            return None, "Unsupported OAuth provider"
        
        if not user_data:
            return None, "Failed to get user data"
        
        # Check if OAuth account exists
        oauth_account = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.account_id == user_data["id"]
        ).first()
        
        if oauth_account:
            # Update existing account
            oauth_account.access_token = user_data["access_token"]
            oauth_account.refresh_token = user_data.get("refresh_token")
            oauth_account.expires_at = datetime.utcnow() + timedelta(
                seconds=user_data.get("expires_in", 3600)
            )
            db.commit()
            return oauth_account.user, None
        
        # Check if user exists with same email
        user = db.query(User).filter(User.email == user_data["email"]).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_data["email"],
                username=user_data.get("username", user_data["email"].split("@")[0]),
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create OAuth account
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            account_id=user_data["id"],
            account_email=user_data["email"],
            access_token=user_data["access_token"],
            refresh_token=user_data.get("refresh_token"),
            expires_at=datetime.utcnow() + timedelta(
                seconds=user_data.get("expires_in", 3600)
            )
        )
        
        db.add(oauth_account)
        db.commit()
        
        return user, None
        
    except Exception as e:
        return None, str(e)

async def handle_github_callback(code: str) -> Optional[dict]:
    """Handle GitHub OAuth callback."""
    try:
        token = await oauth.github.authorize_access_token(code)
        resp = await oauth.github.get('user')
        profile = resp.json()
        
        # Get primary email
        emails = await oauth.github.get('user/emails')
        primary_email = next(
            (email for email in emails.json() if email["primary"]),
            None
        )
        
        if not primary_email:
            return None
        
        return {
            "id": str(profile["id"]),
            "email": primary_email["email"],
            "username": profile["login"],
            "access_token": token["access_token"],
        }
    except:
        return None

async def handle_google_callback(code: str) -> Optional[dict]:
    """Handle Google OAuth callback."""
    try:
        token = await oauth.google.authorize_access_token(code)
        user_info = await oauth.google.parse_id_token(token)
        
        return {
            "id": user_info["sub"],
            "email": user_info["email"],
            "username": user_info["email"].split("@")[0],
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_in": token.get("expires_in", 3600)
        }
    except:
        return None

def refresh_oauth_token(
    db: Session,
    oauth_account: OAuthAccount
) -> bool:
    """Refresh OAuth access token if expired."""
    if not oauth_account.refresh_token:
        return False
        
    try:
        if oauth_account.provider == "github":
            # GitHub tokens don't expire
            return True
            
        elif oauth_account.provider == "google":
            token = oauth.google.refresh_token(oauth_account.refresh_token)
            
            oauth_account.access_token = token["access_token"]
            oauth_account.refresh_token = token.get("refresh_token", oauth_account.refresh_token)
            oauth_account.expires_at = datetime.utcnow() + timedelta(
                seconds=token.get("expires_in", 3600)
            )
            
            db.commit()
            return True
            
    except:
        return False
        
    return False