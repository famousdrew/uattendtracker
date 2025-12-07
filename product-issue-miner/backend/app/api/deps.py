"""
API dependency functions for database sessions and authentication.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Header, HTTPException, status
import secrets

from app.database import AsyncSessionLocal
from app.config import settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.

    Yields an async database session that automatically commits on success
    and rolls back on error.

    Yields:
        AsyncSession: Database session for the request
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def verify_password(
    x_dashboard_password: str = Header(..., alias="X-Dashboard-Password")
) -> bool:
    """
    Simple password authentication for dashboard.

    Verifies the dashboard password from the X-Dashboard-Password header
    using constant-time comparison to prevent timing attacks.

    Args:
        x_dashboard_password: Password from request header

    Returns:
        bool: True if password is valid

    Raises:
        HTTPException: 401 if password is invalid
    """
    if not secrets.compare_digest(x_dashboard_password, settings.DASHBOARD_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard password"
        )
    return True
