"""
Middleware module for FastAPI application.

Exports all middleware classes for easy import.
"""

from app.middleware.security import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    AuthenticationMiddleware,
    get_request_size_limit,
    get_rate_limits,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "RequestSizeLimitMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "AuthenticationMiddleware",
    "get_request_size_limit",
    "get_rate_limits",
]
