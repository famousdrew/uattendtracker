"""
Background job scheduler for automated ticket sync and analysis.

Uses APScheduler to run periodic jobs:
- Daily sync: Full pipeline at 2 AM (sync -> analyze -> cluster -> trends)
- Hourly trends: Update cluster trends every hour
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import AsyncSessionLocal
from app.services import get_sync_service, get_pipeline

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def daily_sync_job():
    """
    Daily pipeline: sync -> analyze -> cluster -> trends.
    Runs at 2 AM by default.

    This job:
    1. Syncs tickets from Zendesk (incremental)
    2. Analyzes unprocessed tickets using Claude
    3. Clusters issues (if clustering service available)
    4. Updates cluster trends
    """
    logger.info("Starting daily sync job")

    async with AsyncSessionLocal() as db:
        try:
            sync_service = get_sync_service(db)
            pipeline = get_pipeline(db)

            # Run full pipeline (clustering optional)
            results = await pipeline.run_full_pipeline(
                sync_service=sync_service,
                clusterer=None,  # TODO: Add clustering service when available
                backfill_days=None  # Incremental sync
            )

            logger.info(
                f"Daily sync complete: "
                f"synced={results.get('sync', {})}, "
                f"analyzed={results.get('analysis', {})}, "
                f"clustered={results.get('clustering', {})}"
            )

        except Exception as e:
            logger.error(f"Daily sync job failed: {e}", exc_info=True)
            raise


async def hourly_trends_job():
    """
    Update cluster trends hourly.
    Keeps dashboard data fresh.

    Note: This job will be enabled once clustering service is implemented.
    Currently a no-op placeholder.
    """
    logger.info("Starting hourly trends update")

    # TODO: Implement when clustering service is available
    # async with AsyncSessionLocal() as db:
    #     try:
    #         clusterer = get_clusterer(db)
    #         await clusterer.update_cluster_trends()
    #         await clusterer.update_unique_customer_counts()
    #
    #         logger.info("Hourly trends update complete")
    #
    #     except Exception as e:
    #         logger.error(f"Hourly trends job failed: {e}", exc_info=True)
    #         raise

    logger.info("Hourly trends update skipped (clustering not yet implemented)")


def setup_scheduler():
    """
    Configure and start the background scheduler.

    Jobs configured:
    1. Daily sync at 2 AM - Full pipeline execution
    2. Hourly trends - Update cluster statistics (disabled until clustering ready)

    Raises:
        Exception: If scheduler is already running
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Daily full sync at 2 AM
    scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour=2, minute=0),
        id="daily_sync",
        name="Daily Zendesk Sync",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace period
        coalesce=True  # Combine missed runs into one
    )

    # Hourly trends update (disabled for now)
    # Uncomment when clustering service is ready
    # scheduler.add_job(
    #     hourly_trends_job,
    #     IntervalTrigger(hours=1),
    #     id="hourly_trends",
    #     name="Hourly Trends Update",
    #     replace_existing=True,
    #     misfire_grace_time=600,  # 10 minute grace period
    #     coalesce=True
    # )

    scheduler.start()
    logger.info("Background scheduler started successfully")


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    Waits for running jobs to complete before shutting down.
    """
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")
    else:
        logger.info("Scheduler was not running")


def get_job_status() -> list:
    """
    Get status of all scheduled jobs.

    Returns:
        List of job status dictionaries containing:
        - id: Job identifier
        - name: Human-readable job name
        - next_run: ISO-formatted next run time (or None)
        - trigger: Trigger description (cron/interval)

    Example:
        >>> jobs = get_job_status()
        >>> for job in jobs:
        ...     print(f"{job['name']}: next run at {job['next_run']}")
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    return jobs
