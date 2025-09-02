from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.config import settings
import re
from typing import Tuple

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = settings.CSP_POLICY
        
        # HSTS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains; preload"
        
        return response

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.safe_methods = {"GET", "HEAD", "OPTIONS"}
    
    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _get_token_from_headers(self, request: Request) -> Tuple[str, str]:
        """Extract CSRF token from headers or cookies."""
        header_token = request.headers.get("X-CSRF-Token")
        cookie_token = request.cookies.get("csrf_token")
        return header_token, cookie_token
    
    async def dispatch(self, request: Request, call_next):
        if request.method in self.safe_methods:
            # Safe methods don't need CSRF protection
            response = await call_next(request)
            
            # Set CSRF cookie if not present
            if "csrf_token" not in request.cookies:
                response.set_cookie(
                    "csrf_token",
                    self._generate_csrf_token(),
                    httponly=True,
                    secure=True,
                    samesite="Lax"
                )
            
            return response
        
        # For unsafe methods, verify CSRF token
        header_token, cookie_token = self._get_token_from_headers(request)
        
        if not header_token or not cookie_token or header_token != cookie_token:
            return Response(
                status_code=403,
                content="CSRF token validation failed"
            )
        
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        
        self.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[
                f"{settings.PUBLIC_RATE_LIMIT}/minute",
                f"{settings.RATE_LIMIT_BURST}/second"
            ]
        )
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files
        if re.match(r"^/(static|favicon.ico)", request.url.path):
            return await call_next(request)
        
        # Get limits based on authentication
        if request.user.is_authenticated:
            limits = [f"{settings.AUTH_RATE_LIMIT}/minute"]
        else:
            limits = [f"{settings.PUBLIC_RATE_LIMIT}/minute"]
        
        try:
            await self.limiter.check(request, limits=limits)
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers.update(self.limiter.get_headers())
            
            return response
            
        except Exception as e:
            return Response(
                status_code=429,
                content="Rate limit exceeded",
                headers=self.limiter.get_headers()
            )