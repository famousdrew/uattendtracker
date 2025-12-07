"""
Sync API endpoints for triggering and monitoring Zendesk sync operations.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.api.deps import get_db, verify_password
from app.schemas import SyncStatusResponse, SyncTriggerResponse
from app.services import get_sync_service
from app.models import SyncState, Ticket, ExtractedIssue

router = APIRouter(prefix="/sync", tags=["sync"])

# Global flag to track if sync is running
# In production, use Redis or database for distributed systems
_sync_running = False
_sync_progress = None


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    backfill_days: int = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Manually trigger sync (runs in background).

    Starts a background task to sync tickets from Zendesk and analyze them.
    Only one sync can run at a time.

    Args:
        backfill_days: Optional number of days to backfill (overrides incremental sync)
        background_tasks: FastAPI background tasks handler

    Returns:
        SyncTriggerResponse with sync start info
    """
    global _sync_running, _sync_progress

    # Check if sync is already running
    if _sync_running:
        raise HTTPException(
            status_code=409,
            detail="Sync is already running"
        )

    # Validate backfill_days
    if backfill_days is not None and (backfill_days < 1 or backfill_days > 365):
        raise HTTPException(
            status_code=400,
            detail="backfill_days must be between 1 and 365"
        )

    # Mark sync as running
    _sync_running = True
    _sync_progress = "Starting sync..."
    started_at = datetime.utcnow()

    # Define background task
    async def run_sync():
        global _sync_running, _sync_progress
        try:
            _sync_progress = "Initializing sync service..."

            # Create new session for background task
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as bg_session:
                # Create sync service with the session
                sync_service = get_sync_service(bg_session)

                if backfill_days:
                    _sync_progress = f"Running backfill sync ({backfill_days} days)..."
                else:
                    _sync_progress = "Running incremental sync..."

                # sync_tickets handles both backfill and incremental modes
                result = await sync_service.sync_tickets(backfill_days=backfill_days)
                _sync_progress = f"Sync completed: {result.get('tickets_synced', 0)} tickets synced"

        except Exception as e:
            _sync_progress = f"Sync failed: {str(e)}"
            # Log error with traceback in production
            import traceback
            print(f"Sync error: {e}")
            traceback.print_exc()
        finally:
            _sync_running = False

    # Add task to background tasks
    if background_tasks:
        background_tasks.add_task(run_sync)
    else:
        # For testing without background tasks
        import asyncio
        asyncio.create_task(run_sync())

    return SyncTriggerResponse(
        message="Sync triggered successfully",
        backfill_days=backfill_days,
        started_at=started_at
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_password)
):
    """
    Get last sync info and current progress.

    Returns:
    - Last sync timestamp
    - Last ticket updated timestamp
    - Number of tickets synced
    - Number of issues extracted
    - Current sync status (running/idle)
    - Current progress message if running
    """
    global _sync_running, _sync_progress

    # Get latest sync state
    sync_state_query = select(SyncState).order_by(SyncState.sync_completed_at.desc()).limit(1)
    result = await db.execute(sync_state_query)
    sync_state = result.scalar_one_or_none()

    # Count total tickets and issues
    tickets_count_query = select(func.count()).select_from(Ticket)
    tickets_result = await db.execute(tickets_count_query)
    total_tickets = tickets_result.scalar_one()

    issues_count_query = select(func.count()).select_from(ExtractedIssue)
    issues_result = await db.execute(issues_count_query)
    total_issues = issues_result.scalar_one()

    return SyncStatusResponse(
        last_sync_at=sync_state.sync_completed_at if sync_state else None,
        last_ticket_updated_at=sync_state.last_ticket_updated_at if sync_state else None,
        tickets_synced=total_tickets,
        issues_extracted=total_issues,
        is_running=_sync_running,
        current_progress=_sync_progress if _sync_running else None
    )
