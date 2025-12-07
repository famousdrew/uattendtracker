"""
Main API router aggregating all endpoint modules.
"""

from fastapi import APIRouter

from app.api import issues, clusters, tickets, sync, export

# Create main API router with /api prefix
api_router = APIRouter(prefix="/api")

# Include all sub-routers
api_router.include_router(issues.router)
api_router.include_router(clusters.router)
api_router.include_router(tickets.router)
api_router.include_router(sync.router)
api_router.include_router(export.router)
