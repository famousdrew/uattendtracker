"""
Background tasks API endpoints.

Provides endpoints to:
- View scheduler status and upcoming jobs
- Manually trigger background tasks
- Check task execution status and progress
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.tasks import get_job_status, background_worker

router = APIRouter()


# Response schemas
class JobStatusResponse(BaseModel):
    """Status of a scheduled job."""
    id: str
    name: str
    next_run: Optional[str] = None
    trigger: str


class WorkerStatusResponse(BaseModel):
    """Status of background worker."""
    status: str = Field(..., description="Worker status: idle, running, completed, failed")
    progress: Optional[str] = Field(None, description="Current progress message")
    is_running: bool = Field(..., description="Whether a task is currently executing")
    started_at: Optional[str] = Field(None, description="Task start timestamp (ISO)")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp (ISO)")
    last_result: Optional[dict] = Field(None, description="Result from last completed task")
    last_error: Optional[str] = Field(None, description="Error from last failed task")


class TaskTriggerRequest(BaseModel):
    """Request to trigger a background task."""
    backfill_days: Optional[int] = Field(None, description="Days to backfill (None for incremental)")
    batch_size: int = Field(500, description="Batch size for analysis", ge=1, le=1000)


class TaskTriggerResponse(BaseModel):
    """Response when triggering a task."""
    message: str
    task: str
    status: str


# Endpoints

@router.get("/scheduler/status", response_model=list[JobStatusResponse])
async def get_scheduler_status():
    """
    Get status of all scheduled jobs.

    Returns information about configured jobs including:
    - Job ID and name
    - Next scheduled run time
    - Trigger configuration (cron/interval)

    Example response:
    ```json
    [
        {
            "id": "daily_sync",
            "name": "Daily Zendesk Sync",
            "next_run": "2024-01-15T02:00:00",
            "trigger": "cron[hour='2', minute='0']"
        }
    ]
    ```
    """
    jobs = get_job_status()
    return jobs


@router.get("/worker/status", response_model=WorkerStatusResponse)
async def get_worker_status():
    """
    Get current status of background worker.

    Returns:
    - Current status (idle, running, completed, failed)
    - Progress message if running
    - Timestamps for current or last task
    - Results or errors from last task

    Example response:
    ```json
    {
        "status": "running",
        "progress": "Analyzing tickets (batch size: 500)...",
        "is_running": true,
        "started_at": "2024-01-15T14:30:00",
        "completed_at": null,
        "last_result": null,
        "last_error": null
    }
    ```
    """
    return background_worker.get_status()


@router.post("/sync", response_model=TaskTriggerResponse)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    request: TaskTriggerRequest = TaskTriggerRequest()
):
    """
    Manually trigger a Zendesk ticket sync.

    Request body:
    ```json
    {
        "backfill_days": 7  // Optional: number of days to backfill
    }
    ```

    The sync will run in the background. Use GET /api/tasks/worker/status
    to check progress and results.

    Raises:
        400: If a task is already running
    """
    if background_worker.is_running:
        raise HTTPException(
            status_code=400,
            detail="A background task is already running. Please wait for it to complete."
        )

    # Schedule the task to run in background
    background_tasks.add_task(background_worker.run_sync, request.backfill_days)

    return TaskTriggerResponse(
        message="Sync task started",
        task="sync",
        status="started"
    )


@router.post("/analyze", response_model=TaskTriggerResponse)
async def trigger_analysis(
    background_tasks: BackgroundTasks,
    request: TaskTriggerRequest = TaskTriggerRequest()
):
    """
    Manually trigger ticket analysis.

    Request body:
    ```json
    {
        "batch_size": 500  // Optional: max tickets to analyze
    }
    ```

    The analysis will run in the background. Use GET /api/tasks/worker/status
    to check progress and results.

    Raises:
        400: If a task is already running
    """
    if background_worker.is_running:
        raise HTTPException(
            status_code=400,
            detail="A background task is already running. Please wait for it to complete."
        )

    # Schedule the task to run in background
    background_tasks.add_task(background_worker.run_analysis, request.batch_size)

    return TaskTriggerResponse(
        message="Analysis task started",
        task="analysis",
        status="started"
    )


@router.post("/pipeline", response_model=TaskTriggerResponse)
async def trigger_full_pipeline(
    background_tasks: BackgroundTasks,
    request: TaskTriggerRequest = TaskTriggerRequest()
):
    """
    Manually trigger full pipeline: sync -> analyze -> cluster -> trends.

    Request body:
    ```json
    {
        "backfill_days": 7,  // Optional: days to backfill
        "batch_size": 500    // Optional: max tickets to analyze
    }
    ```

    The pipeline will run in the background. Use GET /api/tasks/worker/status
    to check progress and results.

    Raises:
        400: If a task is already running
    """
    if background_worker.is_running:
        raise HTTPException(
            status_code=400,
            detail="A background task is already running. Please wait for it to complete."
        )

    # Schedule the task to run in background
    background_tasks.add_task(
        background_worker.run_full_pipeline,
        request.backfill_days,
        request.batch_size
    )

    return TaskTriggerResponse(
        message="Full pipeline started",
        task="pipeline",
        status="started"
    )
