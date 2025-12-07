# Background Tasks & Scheduler

This module provides automated background job scheduling and on-demand task execution for the Product Issue Miner application.

## Architecture

The tasks module consists of two main components:

### 1. Scheduler (`scheduler.py`)
Automated periodic jobs using APScheduler:
- **Daily Sync Job**: Runs at 2 AM daily
  - Syncs tickets from Zendesk (incremental)
  - Analyzes unprocessed tickets using Claude AI
  - Clusters issues (when clustering service available)
  - Updates cluster trends

- **Hourly Trends Job**: Runs every hour (currently disabled)
  - Updates cluster statistics
  - Recalculates unique customer counts
  - Keeps dashboard data fresh

### 2. Worker (`worker.py`)
On-demand task execution via API endpoints:
- Manual sync triggers
- Manual analysis triggers
- Full pipeline execution
- Status and progress tracking

## Usage

### Starting the Scheduler

The scheduler starts automatically when the FastAPI application starts:

```python
from app.tasks import setup_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
```

### API Endpoints

#### Get Scheduler Status
```bash
GET /api/tasks/scheduler/status
```

Returns information about scheduled jobs:
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

#### Get Worker Status
```bash
GET /api/tasks/worker/status
```

Returns current worker status:
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

#### Trigger Sync
```bash
POST /api/tasks/sync
Content-Type: application/json

{
    "backfill_days": 7
}
```

#### Trigger Analysis
```bash
POST /api/tasks/analyze
Content-Type: application/json

{
    "batch_size": 500
}
```

#### Trigger Full Pipeline
```bash
POST /api/tasks/pipeline
Content-Type: application/json

{
    "backfill_days": 7,
    "batch_size": 500
}
```

## Configuration

### Scheduled Job Times

Jobs are configured in `scheduler.py`:

```python
# Daily sync at 2 AM
scheduler.add_job(
    daily_sync_job,
    CronTrigger(hour=2, minute=0),
    id="daily_sync",
    name="Daily Zendesk Sync",
    misfire_grace_time=3600  # 1 hour grace period
)
```

To change the schedule:
1. Modify the `CronTrigger` parameters
2. Restart the application

### Misfire Handling

- **misfire_grace_time**: Jobs that miss their scheduled time will run if started within this grace period
- **coalesce**: Multiple missed runs are combined into a single execution

## Monitoring & Logging

All jobs log to the application logger:

```python
import logging
logger = logging.getLogger(__name__)

# Example log messages
logger.info("Starting daily sync job")
logger.error(f"Daily sync job failed: {e}", exc_info=True)
```

Configure logging in your application settings to capture these logs.

## Error Handling

### Scheduler Jobs
- Errors are logged but don't stop the scheduler
- Failed jobs will retry on next schedule
- Check logs for error details

### Worker Tasks
- Errors are captured in worker status
- Check `last_error` field in status response
- Worker returns to idle state after error

## Testing

### Manual Testing

1. Start the application:
```bash
uvicorn app.main:app --reload
```

2. Check scheduler status:
```bash
curl http://localhost:8000/api/tasks/scheduler/status
```

3. Trigger a manual sync:
```bash
curl -X POST http://localhost:8000/api/tasks/sync \
  -H "Content-Type: application/json" \
  -d '{"backfill_days": 1}'
```

4. Monitor progress:
```bash
curl http://localhost:8000/api/tasks/worker/status
```

### Integration Testing

Example test for scheduler:

```python
import pytest
from app.tasks import setup_scheduler, shutdown_scheduler, get_job_status

@pytest.fixture
async def scheduler():
    setup_scheduler()
    yield
    shutdown_scheduler()

async def test_scheduler_status(scheduler):
    jobs = get_job_status()
    assert len(jobs) > 0
    assert any(job["id"] == "daily_sync" for job in jobs)
```

## Future Enhancements

### Clustering Integration

Once the clustering service is implemented:

1. Update `get_clusterer` import in `scheduler.py`:
```python
from app.services import get_clusterer
```

2. Enable clustering in `daily_sync_job`:
```python
clusterer = get_clusterer(db)
results = await pipeline.run_full_pipeline(
    sync_service=sync_service,
    clusterer=clusterer  # Pass clusterer instead of None
)
```

3. Uncomment hourly trends job:
```python
scheduler.add_job(
    hourly_trends_job,
    IntervalTrigger(hours=1),
    id="hourly_trends",
    name="Hourly Trends Update"
)
```

### Additional Jobs

Examples of jobs you might add:

```python
# Weekly report generation
scheduler.add_job(
    weekly_report_job,
    CronTrigger(day_of_week='mon', hour=9),
    id="weekly_report"
)

# Data cleanup (monthly)
scheduler.add_job(
    cleanup_old_data,
    CronTrigger(day=1, hour=3),
    id="monthly_cleanup"
)

# Health check (every 5 minutes)
scheduler.add_job(
    health_check_job,
    IntervalTrigger(minutes=5),
    id="health_check"
)
```

## Troubleshooting

### Scheduler Not Starting

Check application logs for errors:
```bash
tail -f logs/app.log | grep scheduler
```

Common issues:
- Database connection errors
- Missing dependencies (APScheduler)
- Port conflicts

### Jobs Not Running

1. Verify scheduler is running:
```bash
curl http://localhost:8000/api/tasks/scheduler/status
```

2. Check `next_run` time in status response

3. Check application logs for errors

### Worker Stuck in "Running" State

If a worker task crashes without updating status:

1. Restart the application (worker state will reset)
2. Check logs for the failure reason
3. Fix the underlying issue before retrying

## Performance Considerations

### Database Sessions

Each job creates its own database session:
```python
async with AsyncSessionLocal() as db:
    # Job logic here
```

Sessions are automatically closed when the job completes.

### Batch Processing

Analysis jobs process tickets in batches to avoid memory issues:
```python
await pipeline.analyze_unprocessed_tickets(batch_size=500)
```

Adjust `batch_size` based on:
- Available memory
- API rate limits (Claude AI)
- Desired processing time

### Concurrency

- Only one worker task can run at a time
- Scheduled jobs run concurrently with worker tasks
- Use worker status to prevent conflicts

## Security

### API Access Control

Add authentication to task endpoints:

```python
from fastapi import Depends
from app.auth import get_admin_user

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    request: TaskTriggerRequest,
    user: User = Depends(get_admin_user)  # Require admin
):
    # ...
```

### Rate Limiting

Prevent abuse of manual trigger endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/sync")
@limiter.limit("5/hour")  # Max 5 syncs per hour
async def trigger_sync(...):
    # ...
```

## References

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [SQLAlchemy Async Sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
