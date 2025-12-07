"""
Background tasks and scheduling module.

Provides:
- Scheduler: Automated periodic jobs (daily sync, hourly trends)
- Worker: On-demand background task execution via API
"""

from app.tasks.scheduler import (
    scheduler,
    setup_scheduler,
    shutdown_scheduler,
    get_job_status,
    daily_sync_job,
    hourly_trends_job
)
from app.tasks.worker import (
    background_worker,
    BackgroundWorker
)

__all__ = [
    # Scheduler
    "scheduler",
    "setup_scheduler",
    "shutdown_scheduler",
    "get_job_status",
    "daily_sync_job",
    "hourly_trends_job",
    # Worker
    "background_worker",
    "BackgroundWorker"
]
