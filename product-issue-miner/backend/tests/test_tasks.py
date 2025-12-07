"""
Tests for background tasks and scheduler.

Tests the scheduler setup, worker functionality, and API endpoints.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks import (
    setup_scheduler,
    shutdown_scheduler,
    get_job_status,
    background_worker,
    BackgroundWorker
)


class TestScheduler:
    """Test scheduler configuration and management."""

    def test_setup_scheduler(self):
        """Test scheduler starts successfully."""
        setup_scheduler()

        jobs = get_job_status()
        assert len(jobs) > 0
        assert any(job["id"] == "daily_sync" for job in jobs)

        shutdown_scheduler()

    def test_get_job_status(self):
        """Test job status retrieval."""
        setup_scheduler()

        jobs = get_job_status()
        assert isinstance(jobs, list)

        if jobs:
            job = jobs[0]
            assert "id" in job
            assert "name" in job
            assert "trigger" in job
            # next_run may be None if scheduler is paused

        shutdown_scheduler()

    def test_shutdown_scheduler(self):
        """Test scheduler shuts down gracefully."""
        setup_scheduler()
        shutdown_scheduler()

        # Should be safe to call multiple times
        shutdown_scheduler()


class TestBackgroundWorker:
    """Test background worker functionality."""

    def test_worker_initial_state(self):
        """Test worker starts in idle state."""
        worker = BackgroundWorker()

        assert worker.status == "idle"
        assert worker.progress is None
        assert not worker.is_running
        assert worker.last_result is None
        assert worker.last_error is None

    def test_get_status(self):
        """Test worker status retrieval."""
        worker = BackgroundWorker()
        status = worker.get_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "progress" in status
        assert "is_running" in status
        assert "started_at" in status
        assert "completed_at" in status
        assert "last_result" in status
        assert "last_error" in status

    @pytest.mark.asyncio
    async def test_run_sync_success(self):
        """Test successful sync execution."""
        worker = BackgroundWorker()

        # Mock the sync service
        mock_result = {
            "tickets_synced": 10,
            "tickets_updated": 5,
            "errors": 0
        }

        with patch("app.tasks.worker.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.worker.get_sync_service") as mock_get_sync:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_sync = AsyncMock()
            mock_sync.sync_tickets.return_value = mock_result
            mock_get_sync.return_value = mock_sync

            result = await worker.run_sync(backfill_days=7)

            assert result == mock_result
            assert worker.status == "completed"
            assert worker.last_result == mock_result
            assert worker.last_error is None

    @pytest.mark.asyncio
    async def test_run_sync_failure(self):
        """Test sync failure handling."""
        worker = BackgroundWorker()

        with patch("app.tasks.worker.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.worker.get_sync_service") as mock_get_sync:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Simulate failure
            mock_sync = AsyncMock()
            mock_sync.sync_tickets.side_effect = Exception("Sync failed")
            mock_get_sync.return_value = mock_sync

            with pytest.raises(Exception, match="Sync failed"):
                await worker.run_sync()

            assert worker.status == "failed"
            assert worker.last_error == "Sync failed"

    @pytest.mark.asyncio
    async def test_concurrent_task_prevention(self):
        """Test that only one task can run at a time."""
        worker = BackgroundWorker()

        with patch("app.tasks.worker.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.worker.get_sync_service") as mock_get_sync:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock slow sync
            mock_sync = AsyncMock()
            async def slow_sync(*args, **kwargs):
                await asyncio.sleep(1)
                return {"tickets_synced": 0}

            mock_sync.sync_tickets = slow_sync
            mock_get_sync.return_value = mock_sync

            # Start first task (don't await)
            import asyncio
            task1 = asyncio.create_task(worker.run_sync())

            # Try to start second task
            with pytest.raises(RuntimeError, match="already running"):
                await worker.run_sync()

            # Wait for first task to complete
            await task1

    @pytest.mark.asyncio
    async def test_run_analysis_success(self):
        """Test successful analysis execution."""
        worker = BackgroundWorker()

        mock_result = {
            "tickets_processed": 50,
            "issues_extracted": 75,
            "errors": 0
        }

        with patch("app.tasks.worker.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.worker.get_pipeline") as mock_get_pipeline:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_pipeline = AsyncMock()
            mock_pipeline.analyze_unprocessed_tickets.return_value = mock_result
            mock_get_pipeline.return_value = mock_pipeline

            result = await worker.run_analysis(batch_size=100)

            assert result == mock_result
            assert worker.status == "completed"
            mock_pipeline.analyze_unprocessed_tickets.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_run_full_pipeline_success(self):
        """Test successful full pipeline execution."""
        worker = BackgroundWorker()

        sync_result = {"tickets_synced": 10}
        analysis_result = {"tickets_processed": 10, "issues_extracted": 15}

        with patch("app.tasks.worker.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.worker.get_sync_service") as mock_get_sync, \
             patch("app.tasks.worker.get_pipeline") as mock_get_pipeline:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_sync = AsyncMock()
            mock_sync.sync_tickets.return_value = sync_result
            mock_get_sync.return_value = mock_sync

            mock_pipeline = AsyncMock()
            mock_pipeline.analyze_unprocessed_tickets.return_value = analysis_result
            mock_get_pipeline.return_value = mock_pipeline

            result = await worker.run_full_pipeline(backfill_days=7, batch_size=500)

            assert result["sync"] == sync_result
            assert result["analysis"] == analysis_result
            assert "clustering" in result
            assert worker.status == "completed"


class TestScheduledJobs:
    """Test scheduled job functions."""

    @pytest.mark.asyncio
    async def test_daily_sync_job(self):
        """Test daily sync job execution."""
        from app.tasks.scheduler import daily_sync_job

        with patch("app.tasks.scheduler.AsyncSessionLocal") as mock_session, \
             patch("app.tasks.scheduler.get_sync_service") as mock_get_sync, \
             patch("app.tasks.scheduler.get_pipeline") as mock_get_pipeline:

            mock_db = MagicMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_sync = AsyncMock()
            mock_get_sync.return_value = mock_sync

            mock_pipeline = AsyncMock()
            mock_pipeline.run_full_pipeline.return_value = {
                "sync": {"tickets_synced": 5},
                "analysis": {"tickets_processed": 5},
                "clustering": {"skipped": True}
            }
            mock_get_pipeline.return_value = mock_pipeline

            # Should not raise
            await daily_sync_job()

            mock_pipeline.run_full_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_hourly_trends_job(self):
        """Test hourly trends job (currently no-op)."""
        from app.tasks.scheduler import hourly_trends_job

        # Should not raise (currently just logs)
        await hourly_trends_job()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
