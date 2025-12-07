# Background Scheduler - Verification Checklist

## Installation Verification

### Files Created ✓

- [x] `app/tasks/scheduler.py` - APScheduler configuration and jobs
- [x] `app/tasks/worker.py` - Background worker implementation
- [x] `app/tasks/__init__.py` - Module exports
- [x] `app/api/tasks.py` - REST API endpoints
- [x] `tests/test_tasks.py` - Unit tests
- [x] `examples/test_scheduler.py` - Example script
- [x] `app/tasks/README.md` - Detailed documentation
- [x] `app/tasks/ARCHITECTURE.md` - System architecture
- [x] `app/tasks/QUICK_REFERENCE.md` - Quick reference guide
- [x] `SCHEDULER_SETUP.md` - Setup documentation

### Integration Points ✓

- [x] Scheduler imported in `app/main.py` (line 11)
- [x] `setup_scheduler()` called in lifespan startup (line 50)
- [x] `shutdown_scheduler()` called in lifespan shutdown (line 57)
- [x] Tasks router included in FastAPI app (line 152)
- [x] API endpoints available at `/api/tasks/*`

### Dependencies ✓

- [x] APScheduler 3.10.4 in `requirements.txt` (line 12)
- [x] All other dependencies already installed

## Functional Verification

### Step 1: Syntax Check ✓

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
python -m py_compile app/tasks/scheduler.py
python -m py_compile app/tasks/worker.py
python -m py_compile app/api/tasks.py
python -m py_compile tests/test_tasks.py
```

**Status:** PASSED (no syntax errors)

### Step 2: Import Check

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
python -c "from app.tasks import setup_scheduler, shutdown_scheduler, get_job_status, background_worker; print('OK')"
```

**Expected:** `OK`

### Step 3: Application Startup

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
uvicorn app.main:app --reload
```

**Expected logs:**
```
Starting up Product Issue Miner API...
Background scheduler started successfully
Startup complete
```

**Status:** Run this to verify

### Step 4: API Documentation

Open browser: http://localhost:8000/docs

**Expected:**
- "Background Tasks" section visible
- 5 endpoints listed:
  - GET /api/tasks/scheduler/status
  - GET /api/tasks/worker/status
  - POST /api/tasks/sync
  - POST /api/tasks/analyze
  - POST /api/tasks/pipeline

**Status:** Verify after starting app

### Step 5: Scheduler Status

```bash
curl http://localhost:8000/api/tasks/scheduler/status
```

**Expected:**
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

**Status:** Verify after starting app

### Step 6: Worker Status

```bash
curl http://localhost:8000/api/tasks/worker/status
```

**Expected:**
```json
{
    "status": "idle",
    "progress": null,
    "is_running": false,
    "started_at": null,
    "completed_at": null,
    "last_result": null,
    "last_error": null
}
```

**Status:** Verify after starting app

### Step 7: Manual Task Trigger

```bash
curl -X POST http://localhost:8000/api/tasks/sync \
  -H "Content-Type: application/json" \
  -d '{"backfill_days": 1}'
```

**Expected:**
```json
{
    "message": "Sync task started",
    "task": "sync",
    "status": "started"
}
```

**Status:** Verify after starting app

### Step 8: Worker Progress

```bash
curl http://localhost:8000/api/tasks/worker/status
```

**Expected (while running):**
```json
{
    "status": "running",
    "progress": "Syncing tickets (backfill: 1)...",
    "is_running": true,
    "started_at": "2024-01-15T14:30:00",
    ...
}
```

**Status:** Verify after triggering task

### Step 9: Run Tests

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
pytest tests/test_tasks.py -v
```

**Expected:**
- All tests pass
- No import errors
- No syntax errors

**Status:** Run to verify

### Step 10: Example Script

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
python examples/test_scheduler.py
```

**Expected:**
- Scheduler starts successfully
- Jobs listed
- No errors
- Clean shutdown

**Status:** Run to verify

## Feature Verification

### Scheduled Jobs

- [x] Daily sync job configured (2 AM)
- [x] Misfire handling configured (1 hour grace)
- [x] Coalesce enabled (multiple missed runs combined)
- [ ] Hourly trends job (disabled - pending clustering)

### Worker Operations

- [x] `run_sync()` - Sync tickets from Zendesk
- [x] `run_analysis()` - Analyze tickets with Claude AI
- [x] `run_full_pipeline()` - Complete pipeline
- [x] Status tracking (idle/running/completed/failed)
- [x] Progress messages
- [x] Result and error capture
- [x] Concurrent task prevention

### API Endpoints

- [x] GET /api/tasks/scheduler/status - View scheduled jobs
- [x] GET /api/tasks/worker/status - Check worker status
- [x] POST /api/tasks/sync - Trigger sync manually
- [x] POST /api/tasks/analyze - Trigger analysis manually
- [x] POST /api/tasks/pipeline - Trigger full pipeline

### Error Handling

- [x] Scheduler job errors logged (don't crash scheduler)
- [x] Worker task errors captured in status
- [x] Database session cleanup
- [x] Graceful shutdown
- [x] Concurrent task prevention

### Documentation

- [x] Comprehensive README.md
- [x] Architecture diagrams
- [x] Quick reference guide
- [x] Setup documentation
- [x] API examples
- [x] Testing guide
- [x] Troubleshooting section

## Integration Verification

### Database Integration

- [x] Uses `AsyncSessionLocal` for sessions
- [x] Session context managers for cleanup
- [x] Connection pooling configured
- [x] Async operations throughout

### Service Integration

- [x] Uses `get_sync_service(db)` for Zendesk sync
- [x] Uses `get_pipeline(db)` for analysis
- [x] Ready for `get_clusterer(db)` when available
- [x] All services use async patterns

### FastAPI Integration

- [x] Scheduler starts in lifespan context
- [x] Scheduler stops in lifespan context
- [x] API router included
- [x] Background tasks for async execution
- [x] Proper HTTP status codes
- [x] Pydantic schemas for validation

## Performance Verification

### Configuration

- [x] Batch size configurable (default 500)
- [x] Backfill days configurable
- [x] Commit frequency optimized (every 10 tickets)
- [x] Connection pooling enabled
- [x] Proper async/await usage

### Resource Management

- [x] Database sessions auto-close
- [x] One worker task at a time
- [x] Scheduler jobs independent
- [x] Memory-efficient batching

## Security Verification

### Current State

- [x] No hardcoded credentials
- [x] Uses environment variables
- [x] Database sessions isolated
- [x] Error messages sanitized

### Future Enhancements (TODO)

- [ ] Add authentication to task endpoints
- [ ] Add rate limiting for manual triggers
- [ ] Add audit logging
- [ ] Add admin-only access control

## Deployment Readiness

### Development

- [x] Works with `uvicorn --reload`
- [x] Logging configured
- [x] Tests included
- [x] Examples provided

### Production Considerations

- [ ] Configure log rotation
- [ ] Set up monitoring/alerting
- [ ] Configure error reporting (e.g., Sentry)
- [ ] Add health check endpoints
- [ ] Configure backup scheduler
- [ ] Set up metrics collection

## Known Limitations

### Current Limitations

1. **Clustering Disabled**
   - Hourly trends job disabled
   - Clustering step skipped in pipeline
   - Ready for integration when clustering service available

2. **Single Worker**
   - Only one manual task at a time
   - Prevents resource conflicts
   - Consider multiple workers if needed

3. **No Persistent State**
   - Worker state resets on restart
   - Job history not stored
   - Add persistence if needed

### Future Enhancements

1. **Add clustering integration** when service ready
2. **Add webhook notifications** for job completion
3. **Add metrics collection** for monitoring
4. **Add job history/audit log** in database
5. **Add configurable schedules** via admin UI
6. **Add job retry logic** with exponential backoff

## Testing Checklist

### Unit Tests

```bash
pytest tests/test_tasks.py::TestScheduler -v
pytest tests/test_tasks.py::TestBackgroundWorker -v
pytest tests/test_tasks.py::TestScheduledJobs -v
```

### Integration Tests

1. Start application
2. Verify scheduler started
3. Check API endpoints respond
4. Trigger manual sync
5. Monitor worker status
6. Wait for completion
7. Verify results

### Manual Tests

1. Run example script
2. Check logs for errors
3. Verify scheduled job times
4. Test error handling (e.g., invalid backfill_days)
5. Test concurrent task prevention

## Sign-off

### Development Environment

- [ ] All files created successfully
- [ ] Syntax validation passed
- [ ] Imports work correctly
- [ ] Application starts without errors
- [ ] API endpoints accessible
- [ ] Tests pass
- [ ] Examples run successfully

### Code Quality

- [ ] Follows async/await patterns
- [ ] Proper error handling
- [ ] Comprehensive logging
- [ ] Type hints included
- [ ] Docstrings present
- [ ] PEP 8 compliant

### Documentation

- [ ] README.md complete
- [ ] Architecture documented
- [ ] API examples provided
- [ ] Quick reference available
- [ ] Setup guide included
- [ ] Troubleshooting covered

## Next Steps

1. **Start the application** and verify all checks above
2. **Run the test suite** to ensure everything works
3. **Test manual triggers** via API
4. **Review logs** for any issues
5. **Update TODO items** as features are added
6. **Integrate clustering** when service is ready

## Support

If any verification step fails:

1. Check the error message and logs
2. Refer to troubleshooting section in README.md
3. Verify all dependencies installed
4. Check database connection
5. Review configuration in .env file

For additional help:
- Review `app/tasks/README.md`
- Check `app/tasks/ARCHITECTURE.md`
- See examples in `examples/test_scheduler.py`
- Run tests for debugging: `pytest tests/test_tasks.py -v --tb=long`
