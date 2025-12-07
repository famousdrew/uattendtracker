"""
Example script to test the background scheduler.

This script demonstrates:
1. Setting up the scheduler
2. Checking job status
3. Manually triggering jobs
4. Using the background worker

Run this script to verify scheduler functionality without starting the full API.
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_scheduler():
    """Test scheduler setup and job status."""
    from app.tasks import setup_scheduler, shutdown_scheduler, get_job_status

    logger.info("Setting up scheduler...")
    setup_scheduler()

    logger.info("Getting job status...")
    jobs = get_job_status()

    for job in jobs:
        logger.info(f"Job: {job['name']}")
        logger.info(f"  ID: {job['id']}")
        logger.info(f"  Next run: {job['next_run']}")
        logger.info(f"  Trigger: {job['trigger']}")
        logger.info("")

    # Wait a few seconds to see if jobs would trigger
    logger.info("Waiting 5 seconds...")
    await asyncio.sleep(5)

    logger.info("Shutting down scheduler...")
    shutdown_scheduler()

    logger.info("Test complete!")


async def test_background_worker():
    """Test background worker functionality."""
    from app.tasks import background_worker

    logger.info("Testing background worker...")

    # Check initial status
    status = background_worker.get_status()
    logger.info(f"Initial status: {status['status']}")
    logger.info(f"Is running: {status['is_running']}")

    # Note: To actually run tasks, you need a database connection
    # This example just shows the worker interface

    logger.info("Worker test complete!")


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Background Scheduler Test Suite")
    logger.info("=" * 60)
    logger.info("")

    await test_scheduler()

    logger.info("")
    logger.info("=" * 60)
    logger.info("")

    await test_background_worker()

    logger.info("")
    logger.info("=" * 60)
    logger.info("All tests complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Ensure we can import app modules
    import sys
    from pathlib import Path

    # Add backend directory to path
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_dir))

    # Run tests
    asyncio.run(main())
