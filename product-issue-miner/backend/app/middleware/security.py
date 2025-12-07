"""
Security middleware for FastAPI application.

Implements comprehensive security controls including:
- Security headers (OWASP recommended)
- Request size limits
- Rate limiting for authentication endpoints
- Request logging (sanitized)
- Authentication via X-Dashboard-Password header
"""

import time
import logging
from typing import Dict, Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

from app.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements OWASP recommended security headers:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable browser XSS protection (legacy)
    - Strict-Transport-Security: Force HTTPS connections
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - deny embedding in frames
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection (legacy header, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS in production (1 year max-age)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy - restrict resource loading
        # Adjust based on your frontend needs
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for some frameworks
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",  # Prevents embedding (complements X-Frame-Options)
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Control browser features and APIs
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent DOS attacks.

    Default limit: 10MB (configurable via settings)
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            max_size: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size and reject if too large."""
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(
                    f"Request size {content_length} exceeds limit {self.max_size} "
                    f"from {request.client.host if request.client else 'unknown'}"
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"Request body too large. Maximum size: {self.max_size} bytes"
                    }
                )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using in-memory storage.

    Implements sliding window rate limiting per IP address.
    Different limits for authentication endpoints vs general API.

    Note: In production, consider using Redis for distributed rate limiting.
    """

    def __init__(
        self,
        app,
        auth_requests_per_minute: int = 5,
        general_requests_per_minute: int = 100,
    ):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            auth_requests_per_minute: Rate limit for auth endpoints
            general_requests_per_minute: Rate limit for general API endpoints
        """
        super().__init__(app)
        self.auth_limit = auth_requests_per_minute
        self.general_limit = general_requests_per_minute

        # In-memory storage: {ip: [(timestamp, endpoint_type), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)

        # Endpoints that require strict rate limiting
        self.auth_endpoints = {"/api/auth", "/api/login", "/api/dashboard"}

    def _clean_old_requests(self, ip: str, window_seconds: int = 60):
        """Remove requests older than the time window."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        self.request_history[ip] = [
            (ts, endpoint_type)
            for ts, endpoint_type in self.request_history[ip]
            if ts > cutoff
        ]

    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an authentication endpoint."""
        return any(path.startswith(auth_path) for auth_path in self.auth_endpoints)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on endpoint type."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limiting for health check
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Determine endpoint type and limit
        is_auth = self._is_auth_endpoint(request.url.path)
        limit = self.auth_limit if is_auth else self.general_limit

        # Clean old requests
        self._clean_old_requests(client_ip)

        # Check rate limit
        recent_requests = [
            (ts, ep_type)
            for ts, ep_type in self.request_history[client_ip]
            if ep_type == ("auth" if is_auth else "general")
        ]

        if len(recent_requests) >= limit:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on "
                f"{'auth' if is_auth else 'general'} endpoint: {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {limit} requests per minute."
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                }
            )

        # Record this request
        self.request_history[client_ip].append(
            (datetime.now(), "auth" if is_auth else "general")
        )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = limit - len(recent_requests) - 1
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests with sanitization of sensitive data.

    Logs:
    - Request method, path, client IP
    - Response status and duration
    - Does NOT log: passwords, tokens, API keys
    """

    SENSITIVE_HEADERS = {
        "authorization",
        "x-dashboard-password",
        "x-api-key",
        "cookie",
        "zendesk_api_token",
        "anthropic_api_key",
    }

    SENSITIVE_PATHS = {
        "/api/auth",
        "/api/login",
    }

    def _sanitize_headers(self, headers: Headers) -> Dict[str, str]:
        """Sanitize sensitive headers for logging."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response with timing."""
        start_time = time.time()

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Skip logging for health checks and docs
        if path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Log request (sanitized)
        logger.info(
            f"Request: {method} {path} from {client_ip}"
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Response: {method} {path} -> {response.status_code} "
                f"({duration_ms:.2f}ms)"
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Error: {method} {path} -> {type(e).__name__}: {str(e)} "
                f"({duration_ms:.2f}ms)"
            )
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Simple password-based authentication via X-Dashboard-Password header.

    Protects all /api/* endpoints except public ones.
    Uses constant-time comparison to prevent timing attacks.

    Note: This is a simple authentication mechanism suitable for internal tools.
    For production applications, consider OAuth 2.0, JWT, or other robust auth.
    """

    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def _constant_time_compare(self, a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal
        """
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)

        return result == 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Verify authentication for protected endpoints."""
        path = request.url.path

        # Skip auth for public paths
        if path in self.PUBLIC_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # Get password from header
        provided_password = request.headers.get("X-Dashboard-Password")

        if not provided_password:
            logger.warning(
                f"Missing authentication header from "
                f"{request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "X-Dashboard-Password"},
            )

        # Verify password using constant-time comparison
        if not self._constant_time_compare(provided_password, settings.DASHBOARD_PASSWORD):
            logger.warning(
                f"Invalid authentication from "
                f"{request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid credentials"},
            )

        # Authentication successful
        return await call_next(request)


def get_request_size_limit() -> int:
    """
    Get request size limit from settings.

    Returns:
        Maximum request size in bytes
    """
    return getattr(settings, "MAX_REQUEST_SIZE", 10 * 1024 * 1024)


def get_rate_limits() -> Dict[str, int]:
    """
    Get rate limits from settings.

    Returns:
        Dictionary with auth_limit and general_limit
    """
    return {
        "auth_limit": getattr(settings, "AUTH_RATE_LIMIT", 5),
        "general_limit": getattr(settings, "GENERAL_RATE_LIMIT", 100),
    }
