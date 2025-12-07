# Background Tasks Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Lifespan Manager                           │ │
│  │                                                               │ │
│  │  Startup:                                                     │ │
│  │    1. Initialize database                                    │ │
│  │    2. setup_scheduler() ──────────┐                          │ │
│  │                                   │                          │ │
│  │  Shutdown:                        │                          │ │
│  │    1. shutdown_scheduler() ───────┤                          │ │
│  │    2. Close database              │                          │ │
│  └───────────────────────────────────┼───────────────────────────┘ │
│                                      │                            │
│  ┌───────────────────────────────────▼───────────────────────────┐ │
│  │                    APScheduler Instance                       │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  Daily Sync Job                                         │ │ │
│  │  │  Trigger: CronTrigger(hour=2, minute=0)                 │ │ │
│  │  │  Function: daily_sync_job()                             │ │ │
│  │  │                                                         │ │ │
│  │  │  Actions:                                               │ │ │
│  │  │  1. Create database session                             │ │ │
│  │  │  2. Get sync_service and pipeline                       │ │ │
│  │  │  3. Run pipeline.run_full_pipeline()                    │ │ │
│  │  │     - Sync tickets from Zendesk                         │ │ │
│  │  │     - Analyze with Claude AI                            │ │ │
│  │  │     - Cluster issues (when available)                   │ │ │
│  │  │     - Update trends                                     │ │ │
│  │  │  4. Log results                                         │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  Hourly Trends Job (Disabled)                           │ │ │
│  │  │  Trigger: IntervalTrigger(hours=1)                      │ │ │
│  │  │  Function: hourly_trends_job()                          │ │ │
│  │  │                                                         │ │ │
│  │  │  Will be enabled when clustering is ready:              │ │ │
│  │  │  1. Get clusterer service                               │ │ │
│  │  │  2. Update cluster trends                               │ │ │
│  │  │  3. Update unique customer counts                       │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                  Background Worker (Singleton)                │ │
│  │                                                               │ │
│  │  State:                                                       │ │
│  │    - status: idle | running | completed | failed             │ │
│  │    - progress: Optional[str]                                 │ │
│  │    - started_at: Optional[datetime]                          │ │
│  │    - completed_at: Optional[datetime]                        │ │
│  │    - last_result: Optional[dict]                             │ │
│  │    - last_error: Optional[str]                               │ │
│  │                                                               │ │
│  │  Methods:                                                     │ │
│  │    - run_sync(backfill_days)                                 │ │
│  │    - run_analysis(batch_size)                                │ │
│  │    - run_full_pipeline(backfill_days, batch_size)            │ │
│  │    - get_status() -> dict                                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      API Routes (/api/tasks)                  │ │
│  │                                                               │ │
│  │  GET  /scheduler/status  ──> get_job_status()                │ │
│  │  GET  /worker/status     ──> background_worker.get_status()  │ │
│  │  POST /sync              ──> background_worker.run_sync()    │ │
│  │  POST /analyze           ──> background_worker.run_analysis()│ │
│  │  POST /pipeline          ──> background_worker.run_full_..() │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Daily Sync Job

```
┌────────────────┐
│  2:00 AM       │
│  Cron Trigger  │
└────────┬───────┘
         │
         ▼
┌────────────────────────────────────────┐
│  daily_sync_job()                      │
│  - Create async database session       │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  Get Services                          │
│  - sync_service = get_sync_service(db) │
│  - pipeline = get_pipeline(db)         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  pipeline.run_full_pipeline()          │
│    sync_service=sync_service           │
│    clusterer=None                      │
└────────┬───────────────────────────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
┌───────────────────┐          ┌───────────────────────┐
│  Step 1: Sync     │          │  Step 2: Analyze      │
│  - Fetch tickets  │──────────>│  - Get unprocessed    │
│    from Zendesk   │          │    tickets            │
│  - Save to DB     │          │  - Call Claude AI     │
│  - Update state   │          │  - Extract issues     │
└───────────────────┘          │  - Save issues to DB  │
                               └───────┬───────────────┘
                                       │
                                       ▼
                               ┌───────────────────────┐
                               │  Step 3: Cluster      │
                               │  (Currently skipped)  │
                               │                       │
                               │  Future:              │
                               │  - Group similar      │
                               │    issues             │
                               │  - Name clusters      │
                               │  - Update trends      │
                               └───────┬───────────────┘
                                       │
                                       ▼
                               ┌───────────────────────┐
                               │  Return Results       │
                               │  {                    │
                               │    sync: {...},       │
                               │    analysis: {...},   │
                               │    clustering: {...}  │
                               │  }                    │
                               └───────────────────────┘
```

## Data Flow - Manual API Trigger

```
┌────────────────────────────────────────┐
│  Client Request                        │
│  POST /api/tasks/sync                  │
│  {                                     │
│    "backfill_days": 7                  │
│  }                                     │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  trigger_sync() endpoint               │
│  - Check if worker is busy             │
│  - Add task to BackgroundTasks         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  Immediate Response                    │
│  {                                     │
│    "message": "Sync task started",     │
│    "task": "sync",                     │
│    "status": "started"                 │
│  }                                     │
└────────────────────────────────────────┘

   Meanwhile, in background...

┌────────────────────────────────────────┐
│  background_worker.run_sync(7)         │
│  - Set status = "running"              │
│  - Set progress = "Starting sync..."   │
│  - Record started_at timestamp         │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  Create database session               │
│  async with AsyncSessionLocal() as db: │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  sync_service.sync_tickets(7)          │
│  - Fetch tickets from last 7 days      │
│  - Save to database                    │
│  - Return statistics                   │
└────────┬───────────────────────────────┘
         │
         ├────────────────┬────────────────┐
         │ Success        │ Failure        │
         ▼                ▼                │
┌────────────────┐  ┌──────────────────┐  │
│  Update Worker │  │  Update Worker   │  │
│  - status =    │  │  - status =      │  │
│    "completed" │  │    "failed"      │  │
│  - last_result │  │  - last_error    │  │
│  - completed_at│  │  - completed_at  │  │
└────────────────┘  └──────────────────┘  │
                                          │
                                          │
    Client polls status:                  │
                                          │
┌────────────────────────────────────────┐│
│  GET /api/tasks/worker/status          ││
└────────┬───────────────────────────────┘│
         │                                │
         ▼                                │
┌────────────────────────────────────────┐│
│  Response                              ││
│  {                                     ││
│    "status": "completed",              ││
│    "progress": null,                   ││
│    "is_running": false,                ││
│    "started_at": "...",                ││
│    "completed_at": "...",              ││
│    "last_result": {                    ││
│      "tickets_synced": 42,             ││
│      "tickets_updated": 5              ││
│    },                                  ││
│    "last_error": null                  ││
│  }                                     ││
└────────────────────────────────────────┘│
```

## Component Interactions

```
┌─────────────────────────────────────────────────────────────┐
│                     External Systems                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐              ┌──────────────────┐    │
│  │  Zendesk API     │              │  Claude AI       │    │
│  │                  │              │  (Anthropic)     │    │
│  │  - Tickets       │              │                  │    │
│  │  - Comments      │              │  - Issue extract │    │
│  │  - Organizations │              │  - Categorize    │    │
│  └────────┬─────────┘              └─────────┬────────┘    │
│           │                                  │             │
└───────────┼──────────────────────────────────┼─────────────┘
            │                                  │
            │                                  │
┌───────────┼──────────────────────────────────┼─────────────┐
│           │         Services Layer           │             │
│           │                                  │             │
│  ┌────────▼─────────┐              ┌────────▼──────────┐  │
│  │  SyncService     │              │  IssueAnalyzer    │  │
│  │                  │              │                   │  │
│  │  - sync_tickets()│              │  - extract_issues │  │
│  │  - get_state()   │              │  - batch_analyze  │  │
│  └────────┬─────────┘              └─────────┬─────────┘  │
│           │                                  │             │
│  ┌────────▼──────────────────────────────────▼─────────┐  │
│  │           AnalysisPipeline                          │  │
│  │                                                     │  │
│  │  - analyze_unprocessed_tickets()                   │  │
│  │  - run_full_pipeline()                             │  │
│  └────────┬────────────────────────────────────────────┘  │
│           │                                               │
└───────────┼───────────────────────────────────────────────┘
            │
            │
┌───────────┼───────────────────────────────────────────────┐
│           │         Tasks Layer                           │
│           │                                               │
│  ┌────────▼─────────┐              ┌────────────────────┐ │
│  │  Scheduler       │              │  BackgroundWorker  │ │
│  │                  │              │                    │ │
│  │  - daily_sync    │              │  - run_sync()      │ │
│  │  - hourly_trends │              │  - run_analysis()  │ │
│  │  - setup()       │              │  - get_status()    │ │
│  │  - shutdown()    │              │                    │ │
│  └──────────────────┘              └────────────────────┘ │
│                                                           │
└───────────────────────────────────────────────────────────┘
            │
            │
┌───────────┼───────────────────────────────────────────────┐
│           │         Database Layer                        │
│           │                                               │
│  ┌────────▼─────────┐                                     │
│  │  AsyncSessionLocal                                     │
│  │                                                        │
│  │  Models:                                              │
│  │  - Ticket                                             │
│  │  - ExtractedIssue                                     │
│  │  - IssueCluster                                       │
│  │  - SyncState                                          │
│  └───────────────────────────────────────────────────────┘│
│                                                           │
└───────────────────────────────────────────────────────────┘
```

## State Management

### Worker State Machine

```
    ┌──────────┐
    │   idle   │ <────────────────┐
    └────┬─────┘                  │
         │                        │
         │ Task started           │
         │                        │
         ▼                        │
    ┌──────────┐                  │
    │ running  │                  │
    └────┬─────┘                  │
         │                        │
         │ Task completed         │
         ├────────┬───────────────┤
         │ Success│ Failure       │
         ▼        ▼               │
    ┌──────────┐ ┌──────────┐    │
    │completed │ │  failed  │    │
    └────┬─────┘ └────┬─────┘    │
         │            │           │
         │ Next task  │ Next task│
         └────────────┴───────────┘
```

### Scheduler State

```
    ┌──────────┐
    │ stopped  │
    └────┬─────┘
         │
         │ setup_scheduler()
         │
         ▼
    ┌──────────┐
    │ running  │ ───┐
    └────┬─────┘    │
         │          │ Jobs execute
         │          │ on schedule
         │          │
         │          └───────────┐
         │                      │
         │ shutdown_scheduler() │
         │                      │
         ▼                      │
    ┌──────────┐                │
    │ shutdown │ <──────────────┘
    └──────────┘
       waiting for
       jobs to finish
```

## Error Handling Strategy

### Scheduler Jobs

```
try:
    # Job logic
    result = await perform_task()
    logger.info(f"Job complete: {result}")

except SpecificError as e:
    # Handle known errors
    logger.error(f"Known error: {e}")
    # Notify admins, send alerts, etc.

except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}", exc_info=True)
    # Don't re-raise - let scheduler continue

finally:
    # Always cleanup
    await cleanup_resources()
```

Jobs log errors but don't crash the scheduler. Next scheduled run will retry.

### Worker Tasks

```
try:
    self._status = "running"
    result = await perform_task()
    self._status = "completed"
    self._last_result = result

except Exception as e:
    self._status = "failed"
    self._last_error = str(e)
    logger.error(f"Task failed: {e}", exc_info=True)
    raise  # Re-raise for caller
```

Worker captures errors in status for API consumers to retrieve.

## Concurrency Model

### Scheduler Jobs
- Run concurrently in separate async tasks
- Each job gets its own database session
- Jobs are independent and don't block each other

### Worker Tasks
- Only one task can run at a time (enforced by `is_running` check)
- API endpoints return 400 if task already running
- Prevents resource exhaustion and conflicts

### Database Sessions
- Each job/task creates its own session
- Sessions use connection pooling
- Pool size: 5 connections, max overflow: 10
- Automatic session cleanup with context managers

## Performance Considerations

### Batch Processing
```python
# Process in batches to avoid memory issues
batch_size = 500
result = await pipeline.analyze_unprocessed_tickets(batch_size)

# Commit every 10 tickets to avoid long transactions
if tickets_processed % 10 == 0:
    await db.commit()
```

### API Rate Limiting
```python
# Respect Zendesk rate limits (700 req/min)
# Built into ZendeskClient with retry logic

# Respect Claude AI rate limits
# Batch requests when possible
```

### Database Optimization
```python
# Use batch operations
await db.execute(insert(...).values([...]))

# Use indexed queries
.where(Ticket.analyzed_at.is_(None))  # analyzed_at is indexed

# Limit result sets
.limit(batch_size)
```

## Monitoring Points

### Metrics to Track
- Job execution duration
- Success/failure rates
- Tickets processed per job
- Issues extracted per ticket
- API call latencies (Zendesk, Claude)
- Database query times
- Error rates by type

### Log Events
- Job start/end
- Task progress updates
- API call results
- Database operations
- Errors and exceptions
- Performance warnings

### Health Checks
- Scheduler running
- Last job execution time
- Worker status
- Database connectivity
- External API availability
