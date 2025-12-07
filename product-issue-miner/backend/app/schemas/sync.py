from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SyncStatusResponse(BaseModel):
    """Response for sync status endpoint."""
    last_sync_at: Optional[datetime] = None
    last_ticket_updated_at: Optional[datetime] = None
    tickets_synced: int
    issues_extracted: int
    is_running: bool = False
    current_progress: Optional[str] = None

class SyncTriggerRequest(BaseModel):
    """Request body for triggering sync."""
    backfill_days: Optional[int] = None

class SyncTriggerResponse(BaseModel):
    """Response for sync trigger endpoint."""
    message: str
    backfill_days: Optional[int] = None
    started_at: datetime
