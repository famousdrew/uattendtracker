# Background Job Scheduler - Setup Complete

## Overview

The background job scheduler has been successfully implemented for the Product Issue Miner application. The scheduler automates ticket syncing, analysis, clustering, and trend updates.

## Files Created

### Core Scheduler Files

1. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\tasks\scheduler.py`**
   - APScheduler configuration and job definitions
   - Daily sync job (runs at 2 AM)
   - Hourly trends job (disabled until clustering ready)
   - Setup and shutdown functions

2. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\tasks\worker.py`**
   - Background worker for on-demand task execution
   - Status and progress tracking
   - Three main operations: sync, analysis, full pipeline

3. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\tasks\__init__.py`**
   - Module exports for clean imports
   - Exposes scheduler and worker interfaces

### API Integration

4. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\api\tasks.py`**
   - REST API endpoints for task management
   - Scheduler status endpoint
   - Worker status endpoint
   - Manual trigger endpoints (sync, analyze, pipeline)

### Documentation & Testing

5. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\tasks\README.md`**
   - Comprehensive documentation
   - API usage examples
   - Configuration guide
   - Troubleshooting tips

6. **`C:\dev\uattendissuetrack\product-issue-miner\backend\tests\test_tasks.py`**
   - Unit tests for scheduler and worker
   - Mock-based testing
   - Async test patterns

7. **`C:\dev\uattendissuetrack\product-issue-miner\backend\examples\test_scheduler.py`**
   - Example script for manual testing
   - Demonstrates scheduler usage

### Modified Files

8. **`C:\dev\uattendissuetrack\product-issue-miner\backend\app\main.py`**
   - Integrated scheduler into FastAPI lifespan
   - Added tasks router to API
   - Scheduler starts/stops with application

## Architecture

### Scheduler Component

```
┌─────────────────────────────────────────────┐
│           APScheduler (AsyncIO)             │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Daily Sync Job (2 AM)              │   │
│  │  - Sync tickets from Zendesk        │   │
│  │  - Analyze with Claude AI           │   │
│  │  - Cluster issues                   │   │
│  │  - Update trends                    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Hourly Trends Job (Every Hour)     │   │
│  │  - Update cluster statistics        │   │
│  │  - Recalculate customer counts      │   │
│  │  (Disabled until clustering ready)  │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### Worker Component

```
┌─────────────────────────────────────────────┐
│         Background Worker (Singleton)       │
├─────────────────────────────────────────────┤
│                                             │
│  Status Tracking:                           │
│  - idle / running / completed / failed      │
│  - Progress messages                        │
│  - Timestamps (started_at, completed_at)    │
│  - Results and errors                       │
│                                             │
│  Operations:                                │
│  - run_sync(backfill_days)                  │
│  - run_analysis(batch_size)                 │
│  - run_full_pipeline(...)                   │
│                                             │
└─────────────────────────────────────────────┘
```

## API Endpoints

### GET /api/tasks/scheduler/status

Get information about scheduled jobs.

**Response:**
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

### GET /api/tasks/worker/status

Check background worker status and progress.

**Response:**
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

### POST /api/tasks/sync

Manually trigger a Zendesk sync.

**Request:**
```json
{
    "backfill_days": 7
}
```

**Response:**
```json
{
    "message": "Sync task started",
    "task": "sync",
    "status": "started"
}
```

### POST /api/tasks/analyze

Manually trigger ticket analysis.

**Request:**
```json
{
    "batch_size": 500
}
```

**Response:**
```json
{
    "message": "Analysis task started",
    "task": "analysis",
    "status": "started"
}
```

### POST /api/tasks/pipeline

Manually trigger the full pipeline.

**Request:**
```json
{
    "backfill_days": 7,
    "batch_size": 500
}
```

**Response:**
```json
{
    "message": "Full pipeline started",
    "task": "pipeline",
    "status": "started"
}
```

## Usage

### Starting the Application

The scheduler starts automatically when you run the FastAPI application:

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
uvicorn app.main:app --reload
```

You should see in the logs:
```
Starting up Product Issue Miner API...
Background scheduler started successfully
Startup complete
```

### Testing the Scheduler

1. **Check scheduler status:**
   ```bash
   curl http://localhost:8000/api/tasks/scheduler/status
   ```

2. **View API documentation:**
   - Navigate to: http://localhost:8000/docs
   - Find the "Background Tasks" section
   - Try the interactive endpoints

3. **Trigger a manual sync:**
   ```bash
   curl -X POST http://localhost:8000/api/tasks/sync \
     -H "Content-Type: application/json" \
     -d '{"backfill_days": 1}'
   ```

4. **Monitor progress:**
   ```bash
   curl http://localhost:8000/api/tasks/worker/status
   ```

### Running Tests

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
pytest tests/test_tasks.py -v
```

### Example Script

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
python examples/test_scheduler.py
```

## Configuration

### Scheduled Job Times

Jobs are configured in `app/tasks/scheduler.py`:

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
1. Edit the `CronTrigger` parameters in `scheduler.py`
2. Restart the application

**Common cron patterns:**
- `CronTrigger(hour=2, minute=0)` - Daily at 2:00 AM
- `CronTrigger(hour='*/6')` - Every 6 hours
- `CronTrigger(day_of_week='mon', hour=9)` - Every Monday at 9:00 AM
- `IntervalTrigger(hours=1)` - Every hour

### Environment Variables

No additional environment variables are required. The scheduler uses existing configuration from `.env`:

- `DATABASE_URL` - For database connections
- `ANTHROPIC_API_KEY` - For Claude AI analysis
- `ZENDESK_*` - For Zendesk API access

## Future Enhancements

### Clustering Integration

Once the clustering service is implemented:

1. **Update scheduler.py:**
   ```python
   from app.services import get_clusterer  # Add this import

   async def daily_sync_job():
       async with AsyncSessionLocal() as db:
           clusterer = get_clusterer(db)
           results = await pipeline.run_full_pipeline(
               sync_service=sync_service,
               clusterer=clusterer  # Pass clusterer
           )
   ```

2. **Enable hourly trends job:**
   Uncomment the hourly trends job in `setup_scheduler()`:
   ```python
   scheduler.add_job(
       hourly_trends_job,
       IntervalTrigger(hours=1),
       id="hourly_trends",
       name="Hourly Trends Update"
   )
   ```

3. **Update hourly_trends_job:**
   Uncomment the implementation in `scheduler.py`

### Additional Jobs

Examples of jobs you might add:

```python
# Weekly report generation
async def weekly_report_job():
    # Generate and email weekly summary
    pass

scheduler.add_job(
    weekly_report_job,
    CronTrigger(day_of_week='mon', hour=9),
    id="weekly_report",
    name="Weekly Report"
)

# Monthly data cleanup
async def cleanup_old_data():
    # Archive or delete old data
    pass

scheduler.add_job(
    cleanup_old_data,
    CronTrigger(day=1, hour=3),
    id="monthly_cleanup",
    name="Monthly Cleanup"
)
```

## Troubleshooting

### Scheduler Not Starting

**Problem:** Application starts but no jobs are scheduled

**Solutions:**
1. Check logs for errors during startup
2. Verify APScheduler is installed: `pip list | grep -i apscheduler`
3. Check for import errors in `app/tasks/scheduler.py`

### Jobs Not Executing

**Problem:** Scheduled jobs don't run at expected times

**Solutions:**
1. Check job status: `GET /api/tasks/scheduler/status`
2. Verify `next_run` time is in the future
3. Check application logs for job execution errors
4. Ensure server time zone is correct

### Worker Stuck in "Running" State

**Problem:** Worker shows `is_running: true` but task is complete

**Solutions:**
1. Restart the application (worker state will reset)
2. Check logs for unhandled exceptions
3. Add timeout handling to long-running tasks

### Database Connection Errors

**Problem:** Jobs fail with database connection errors

**Solutions:**
1. Verify `DATABASE_URL` is correct in `.env`
2. Check database is running and accessible
3. Increase connection pool size in `database.py` if needed

## Best Practices

### Async Patterns

All scheduler jobs and worker tasks use async/await:

```python
async def my_job():
    async with AsyncSessionLocal() as db:
        # Use async operations
        result = await db.execute(query)
```

### Error Handling

Jobs should handle errors gracefully:

```python
async def my_job():
    try:
        # Job logic
        pass
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        # Don't re-raise - let scheduler continue
```

### Database Sessions

Always use context managers for database sessions:

```python
async with AsyncSessionLocal() as db:
    # Session is automatically committed and closed
    pass
```

### Logging

Use structured logging for better monitoring:

```python
logger.info(f"Processing {count} tickets", extra={
    "count": count,
    "batch_id": batch_id
})
```

## Security Considerations

### API Authentication

Currently, task endpoints are unauthenticated. In production, add authentication:

```python
from fastapi import Depends
from app.auth import require_admin

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    request: TaskTriggerRequest,
    user = Depends(require_admin)  # Add auth
):
    # ...
```

### Rate Limiting

Prevent abuse of manual trigger endpoints:

```python
from slowapi import Limiter

@router.post("/sync")
@limiter.limit("5/hour")  # Max 5 syncs per hour
async def trigger_sync(...):
    # ...
```

## Monitoring

### Logs

Monitor application logs for job execution:

```bash
tail -f logs/app.log | grep -E "(scheduler|daily_sync|hourly_trends)"
```

### Metrics

Consider adding metrics for monitoring:
- Job execution duration
- Success/failure rates
- Tickets processed per day
- Error rates

### Alerts

Set up alerts for:
- Job failures
- Long-running jobs
- High error rates
- Worker stuck in running state

## Summary

The background job scheduler is fully implemented and integrated with the Product Issue Miner application. It provides:

- Automated daily ticket sync and analysis
- On-demand task execution via API
- Status monitoring and progress tracking
- Comprehensive documentation and tests

The system is ready for clustering integration once that service is implemented.

For questions or issues, refer to:
- `app/tasks/README.md` - Detailed documentation
- `tests/test_tasks.py` - Test examples
- `examples/test_scheduler.py` - Usage examples
