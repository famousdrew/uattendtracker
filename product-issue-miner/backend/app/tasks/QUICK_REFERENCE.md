# Background Scheduler - Quick Reference

## Files Created

```
app/tasks/
├── __init__.py          # Module exports
├── scheduler.py         # APScheduler setup and jobs
├── worker.py            # Background worker for on-demand tasks
├── README.md            # Comprehensive documentation
├── ARCHITECTURE.md      # System architecture and diagrams
└── QUICK_REFERENCE.md   # This file

app/api/
└── tasks.py             # REST API endpoints

tests/
└── test_tasks.py        # Unit tests

examples/
└── test_scheduler.py    # Manual testing script
```

## Quick Start

### 1. Start the Application
```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
uvicorn app.main:app --reload
```

### 2. Check Scheduler Status
```bash
curl http://localhost:8000/api/tasks/scheduler/status
```

### 3. View API Documentation
Open: http://localhost:8000/docs

## API Endpoints Cheat Sheet

| Method | Endpoint | Purpose | Request Body |
|--------|----------|---------|--------------|
| GET | `/api/tasks/scheduler/status` | View scheduled jobs | None |
| GET | `/api/tasks/worker/status` | Check worker status | None |
| POST | `/api/tasks/sync` | Trigger sync | `{"backfill_days": 7}` |
| POST | `/api/tasks/analyze` | Trigger analysis | `{"batch_size": 500}` |
| POST | `/api/tasks/pipeline` | Trigger full pipeline | `{"backfill_days": 7, "batch_size": 500}` |

## Scheduled Jobs

| Job | Schedule | Function | Status |
|-----|----------|----------|--------|
| Daily Sync | 2:00 AM daily | `daily_sync_job()` | Active |
| Hourly Trends | Every hour | `hourly_trends_job()` | Disabled (pending clustering) |

## Python API

### Check Scheduler Status
```python
from app.tasks import get_job_status

jobs = get_job_status()
for job in jobs:
    print(f"{job['name']}: next run at {job['next_run']}")
```

### Check Worker Status
```python
from app.tasks import background_worker

status = background_worker.get_status()
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}")
```

### Manual Triggers (in async context)
```python
from app.tasks import background_worker

# Sync tickets
result = await background_worker.run_sync(backfill_days=7)

# Analyze tickets
result = await background_worker.run_analysis(batch_size=500)

# Full pipeline
result = await background_worker.run_full_pipeline(
    backfill_days=7,
    batch_size=500
)
```

## Configuration

### Change Schedule Times

Edit `app/tasks/scheduler.py`:

```python
# Daily at 2 AM
CronTrigger(hour=2, minute=0)

# Every 6 hours
CronTrigger(hour='*/6')

# Monday at 9 AM
CronTrigger(day_of_week='mon', hour=9)

# Every hour
IntervalTrigger(hours=1)

# Every 30 minutes
IntervalTrigger(minutes=30)
```

### Batch Sizes

- Default sync: Incremental (backfill_days=None)
- Default analysis: 500 tickets per run
- Adjust based on memory and API limits

## Common Tasks

### Manually Trigger Sync (API)
```bash
curl -X POST http://localhost:8000/api/tasks/sync \
  -H "Content-Type: application/json" \
  -d '{"backfill_days": 7}'
```

### Monitor Progress (API)
```bash
# Poll this endpoint while task runs
curl http://localhost:8000/api/tasks/worker/status
```

### Run Tests
```bash
pytest tests/test_tasks.py -v
```

### View Logs
```bash
# Watch for scheduler events
tail -f logs/app.log | grep -E "(scheduler|daily_sync)"
```

## Troubleshooting

### Problem: Scheduler not starting
**Check:**
- Application logs for errors
- APScheduler installed: `pip list | grep -i apscheduler`
- No import errors in scheduler.py

### Problem: Jobs not running
**Check:**
- Job status: `GET /api/tasks/scheduler/status`
- `next_run` time is in future
- Server time zone is correct

### Problem: Worker stuck
**Solution:**
- Restart application (state resets)
- Check logs for exceptions

### Problem: Database errors
**Check:**
- `DATABASE_URL` in `.env`
- Database is running
- Connection pool size

## Status Codes

### Worker Status
- `idle` - No task running
- `running` - Task in progress
- `completed` - Last task succeeded
- `failed` - Last task failed

### HTTP Responses
- `200` - Success
- `400` - Task already running or invalid request
- `500` - Internal server error

## Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `setup_scheduler()` | scheduler.py | Start scheduler |
| `shutdown_scheduler()` | scheduler.py | Stop scheduler |
| `get_job_status()` | scheduler.py | Get job list |
| `daily_sync_job()` | scheduler.py | Daily sync function |
| `hourly_trends_job()` | scheduler.py | Hourly trends function |
| `background_worker` | worker.py | Global worker instance |
| `BackgroundWorker` | worker.py | Worker class |

## Environment Variables

No new variables needed. Uses existing:
- `DATABASE_URL` - Database connection
- `ANTHROPIC_API_KEY` - Claude AI
- `ZENDESK_*` - Zendesk API credentials

## Next Steps

### Enable Clustering (when ready)

1. **Update scheduler.py:**
   ```python
   from app.services import get_clusterer

   async def daily_sync_job():
       clusterer = get_clusterer(db)
       await pipeline.run_full_pipeline(
           sync_service=sync_service,
           clusterer=clusterer  # Instead of None
       )
   ```

2. **Enable hourly trends:**
   Uncomment in `setup_scheduler()`:
   ```python
   scheduler.add_job(
       hourly_trends_job,
       IntervalTrigger(hours=1),
       id="hourly_trends"
   )
   ```

3. **Update hourly_trends_job:**
   Uncomment implementation in scheduler.py

## Example Workflows

### Initial Backfill
```bash
# Sync last 30 days
curl -X POST http://localhost:8000/api/tasks/pipeline \
  -H "Content-Type: application/json" \
  -d '{"backfill_days": 30, "batch_size": 500}'

# Monitor progress
watch -n 5 curl http://localhost:8000/api/tasks/worker/status
```

### Daily Operations
- Scheduler runs automatically at 2 AM
- Syncs new tickets incrementally
- Analyzes unprocessed tickets
- Updates trends (when clustering ready)

### Manual Analysis
```bash
# Analyze without syncing
curl -X POST http://localhost:8000/api/tasks/analyze \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 100}'
```

## Testing

### Quick Test
```bash
python examples/test_scheduler.py
```

### Full Test Suite
```bash
pytest tests/test_tasks.py -v --tb=short
```

### Interactive Testing
```python
# Start Python REPL
python

>>> from app.tasks import setup_scheduler, get_job_status
>>> setup_scheduler()
>>> jobs = get_job_status()
>>> print(jobs)
>>> from app.tasks import shutdown_scheduler
>>> shutdown_scheduler()
```

## Monitoring

### Health Check
```bash
# Application health
curl http://localhost:8000/health

# Scheduler status
curl http://localhost:8000/api/tasks/scheduler/status

# Worker status
curl http://localhost:8000/api/tasks/worker/status
```

### Metrics to Track
- Jobs executed per day
- Success rate
- Average duration
- Tickets processed
- Issues extracted
- Error rate

## Documentation

- **README.md** - Detailed usage guide
- **ARCHITECTURE.md** - System design and flows
- **SCHEDULER_SETUP.md** - Complete setup documentation
- **QUICK_REFERENCE.md** - This file

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Review documentation in `app/tasks/`
3. Run test suite: `pytest tests/test_tasks.py -v`
4. Check examples: `examples/test_scheduler.py`
