"""
Background worker for manual task execution.

Provides a BackgroundWorker class to run tasks on-demand via API endpoints.
Tasks run asynchronously and track their status and progress.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from app.database import AsyncSessionLocal
from app.services import get_sync_service, get_pipeline

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Handles background task execution with status tracking.

    This worker allows API endpoints to trigger long-running tasks
    without blocking the request. Provides status and progress tracking.

    Attributes:
        status: Current task status (idle, running, completed, failed)
        progress: Human-readable progress message
        is_running: Whether a task is currently executing
    """

    def __init__(self):
        """Initialize worker in idle state."""
        self._current_task: Optional[asyncio.Task] = None
        self._status = "idle"
        self._progress: Optional[str] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    @property
    def status(self) -> str:
        """Get current worker status."""
        return self._status

    @property
    def progress(self) -> Optional[str]:
        """Get current progress message."""
        return self._progress

    @property
    def is_running(self) -> bool:
        """Check if a task is currently running."""
        return self._current_task is not None and not self._current_task.done()

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        """Get result from last completed task."""
        return self._last_result

    @property
    def last_error(self) -> Optional[str]:
        """Get error from last failed task."""
        return self._last_error

    def get_status(self) -> Dict[str, Any]:
        """
        Get complete worker status.

        Returns:
            Dictionary with status, progress, timestamps, and results
        """
        return {
            "status": self._status,
            "progress": self._progress,
            "is_running": self.is_running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
            "last_result": self._last_result,
            "last_error": self._last_error
        }

    async def run_sync(self, backfill_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Run Zendesk ticket sync in background.

        Args:
            backfill_days: Number of days to backfill (None for incremental)

        Returns:
            Sync statistics (tickets synced, updated, errors)

        Raises:
            RuntimeError: If a task is already running
        """
        if self.is_running:
            raise RuntimeError("A task is already running")

        self._status = "running"
        self._progress = "Starting Zendesk sync..."
        self._started_at = datetime.utcnow()
        self._last_result = None
        self._last_error = None

        try:
            async with AsyncSessionLocal() as db:
                sync_service = get_sync_service(db)

                self._progress = f"Syncing tickets (backfill: {backfill_days or 'incremental'})..."
                result = await sync_service.sync_tickets(backfill_days)

            self._status = "completed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_result = result

            logger.info(f"Sync completed: {result}")
            return result

        except Exception as e:
            self._status = "failed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_error = str(e)

            logger.error(f"Sync failed: {e}", exc_info=True)
            raise

    async def run_analysis(self, batch_size: int = 500) -> Dict[str, Any]:
        """
        Run ticket analysis in background.

        Args:
            batch_size: Maximum number of tickets to analyze

        Returns:
            Analysis statistics (tickets processed, issues extracted, errors)

        Raises:
            RuntimeError: If a task is already running
        """
        if self.is_running:
            raise RuntimeError("A task is already running")

        self._status = "running"
        self._progress = "Starting ticket analysis..."
        self._started_at = datetime.utcnow()
        self._last_result = None
        self._last_error = None

        try:
            async with AsyncSessionLocal() as db:
                pipeline = get_pipeline(db)

                self._progress = f"Analyzing tickets (batch size: {batch_size})..."
                result = await pipeline.analyze_unprocessed_tickets(batch_size)

            self._status = "completed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_result = result

            logger.info(f"Analysis completed: {result}")
            return result

        except Exception as e:
            self._status = "failed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_error = str(e)

            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise

    async def run_full_pipeline(
        self,
        backfill_days: Optional[int] = None,
        batch_size: int = 500
    ) -> Dict[str, Any]:
        """
        Run complete pipeline in background: sync -> analyze -> cluster -> trends.

        Args:
            backfill_days: Number of days to backfill (None for incremental)
            batch_size: Maximum number of tickets to analyze

        Returns:
            Combined statistics from all pipeline stages

        Raises:
            RuntimeError: If a task is already running
        """
        if self.is_running:
            raise RuntimeError("A task is already running")

        self._status = "running"
        self._progress = "Starting full pipeline..."
        self._started_at = datetime.utcnow()
        self._last_result = None
        self._last_error = None

        try:
            async with AsyncSessionLocal() as db:
                sync_service = get_sync_service(db)
                pipeline = get_pipeline(db)

                # Step 1: Sync tickets
                self._progress = f"Syncing tickets (backfill: {backfill_days or 'incremental'})..."
                sync_result = await sync_service.sync_tickets(backfill_days)
                logger.info(f"Sync complete: {sync_result}")

                # Step 2: Analyze tickets
                self._progress = f"Analyzing tickets (batch size: {batch_size})..."
                analysis_result = await pipeline.analyze_unprocessed_tickets(batch_size)
                logger.info(f"Analysis complete: {analysis_result}")

                # Step 3: Cluster issues (TODO: implement when clustering service ready)
                self._progress = "Clustering issues..."
                cluster_result = {"skipped": True, "reason": "Clustering not yet implemented"}

                # Step 4: Update trends (TODO: implement when clustering service ready)
                self._progress = "Updating trends..."
                # trends_result = await clusterer.update_cluster_trends()
                # await clusterer.update_unique_customer_counts()

            result = {
                "sync": sync_result,
                "analysis": analysis_result,
                "clustering": cluster_result
            }

            self._status = "completed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_result = result

            logger.info(f"Full pipeline completed: {result}")
            return result

        except Exception as e:
            self._status = "failed"
            self._progress = None
            self._completed_at = datetime.utcnow()
            self._last_error = str(e)

            logger.error(f"Full pipeline failed: {e}", exc_info=True)
            raise


# Global worker instance (singleton)
background_worker = BackgroundWorker()
