"""
Product Issue Miner API - Main FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import close_db, init_db
from app.tasks import setup_scheduler, shutdown_scheduler
from app.middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    AuthenticationMiddleware,
    get_request_size_limit,
    get_rate_limits,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database initialization on startup
    - Background scheduler startup
    - Database connection cleanup on shutdown
    - Background scheduler shutdown
    """
    # Startup
    logger.info("Starting up Product Issue Miner API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"CORS Origins: {settings.cors_origins_list}")

    # Uncomment to auto-create tables (use Alembic in production)
    # await init_db()

    # Start background scheduler
    setup_scheduler()
    logger.info("Startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Product Issue Miner API...")
    shutdown_scheduler()
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Product Issue Miner API",
    description="API for analyzing Zendesk tickets and mining product issues using AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Add security middleware (order matters - applied in reverse)
# 1. Request logging (outermost - logs everything)
app.add_middleware(RequestLoggingMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate limiting
rate_limits = get_rate_limits()
app.add_middleware(
    RateLimitMiddleware,
    auth_requests_per_minute=rate_limits["auth_limit"],
    general_requests_per_minute=rate_limits["general_limit"],
)

# 4. Request size limiting
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size=get_request_size_limit(),
)

# 5. Authentication middleware
app.add_middleware(AuthenticationMiddleware)

# 6. CORS (innermost - must be after auth for credentials)
# In development: allow localhost origins
# In production: restrict to specific frontend URLs
cors_origins = settings.cors_origins_list

# Warn if using wildcard CORS in production
if settings.ENVIRONMENT == "production" and "*" in cors_origins:
    logger.warning(
        "WARNING: CORS is set to allow all origins (*) in production. "
        "This is a security risk. Set CORS_ORIGINS to specific origins."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Dashboard-Password", "Authorization"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": "product-issue-miner-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API information
    """
    return {
        "name": "Product Issue Miner API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routers
from app.api import tasks
from app.api.router import api_router

app.include_router(tasks.router, prefix="/api/tasks", tags=["Background Tasks"])
app.include_router(api_router)
