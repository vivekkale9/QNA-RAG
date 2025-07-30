import time
import logging
from datetime import datetime
from typing import Dict, Optional
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..utils.auth import verify_token

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
        self.failed_logins: Dict[str, list] = defaultdict(list)
        
        # Rate limiting configuration
        self.rate_limit_requests = 100  # requests per minute
        self.rate_limit_window = 60  # seconds
        self.login_attempts_limit = 5  # failed attempts before blocking
        self.login_block_duration = 300  # seconds (5 minutes)
    
    def is_allowed(self, client_ip: str, endpoint: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            client_ip: Client IP address
            endpoint: Request endpoint
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        key = f"{client_ip}:{endpoint}"
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            if now < self.blocked_ips[client_ip].timestamp():
                retry_after = int(self.blocked_ips[client_ip].timestamp() - now)
                return False, retry_after
            else:
                # Unblock IP
                del self.blocked_ips[client_ip]
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                             if now - req_time < self.rate_limit_window]
        
        # Check rate limit
        if len(self.requests[key]) >= self.rate_limit_requests:
            return False, self.rate_limit_window
        
        # Record request
        self.requests[key].append(now)
        return True, None
    
    def record_failed_login(self, client_ip: str):
        """Record a failed login attempt."""
        now = time.time()
        
        # Clean old failed attempts
        self.failed_logins[client_ip] = [
            attempt_time for attempt_time in self.failed_logins[client_ip]
            if now - attempt_time < self.login_block_duration
        ]
        
        # Record new failed attempt
        self.failed_logins[client_ip].append(now)
        
        # Block IP if too many failed attempts
        if len(self.failed_logins[client_ip]) >= self.login_attempts_limit:
            self.blocked_ips[client_ip] = datetime.fromtimestamp(now + self.login_block_duration)
            logger.warning(f"Blocked IP {client_ip} due to {self.login_attempts_limit} failed login attempts")


# Global rate limiter instance
rate_limiter = RateLimiter()

# OAuth2 bearer scheme
oauth2_scheme = HTTPBearer(auto_error=False)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Custom authentication middleware for JWT validation and rate limiting."""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Public paths that don't require authentication
        self.public_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/rag/auth/login",
            "/rag/auth/register",
            "/rag/auth/refresh"
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process the request through authentication and rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response: HTTP response
        """
        start_time = time.time()
        
        # Allow OPTIONS requests (CORS preflight) without authentication
        if request.method == "OPTIONS":
            response = await call_next(request)
            self._add_security_headers(response)
            return response
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Apply rate limiting
        is_allowed, retry_after = rate_limiter.is_allowed(client_ip, request.url.path)
        if not is_allowed:
            return self._rate_limit_response(retry_after)
        
        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            response = await call_next(request)
        else:
            # Authenticate request
            auth_result = await self._authenticate_request(request)
            if auth_result is not True:
                return auth_result  # Return error response
            
            response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        # Add processing time header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    async def _authenticate_request(self, request: Request):
        """
        Authenticate the request using JWT token.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if authenticated, Response object if authentication fails
        """
        try:
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return self._auth_error_response("Missing or invalid authorization header")
            
            # Extract token
            token = auth_header.split(" ")[1]
            
            # Verify token
            payload = verify_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                return self._auth_error_response("Invalid token payload")
            
            # Store user ID in request state for use in route handlers
            request.state.user_id = user_id
            request.state.user_role = payload.get("role")
            
            return True
            
        except HTTPException as e:
            return self._auth_error_response(e.detail)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._auth_error_response("Authentication failed")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _rate_limit_response(self, retry_after: Optional[int]) -> Response:
        """Create rate limit exceeded response."""
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        return Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            media_type="application/json"
        )
    
    def _auth_error_response(self, detail: str) -> Response:
        """Create authentication error response."""
        return Response(
            content=f'{{"detail":"{detail}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            media_type="application/json"
        )
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()" 