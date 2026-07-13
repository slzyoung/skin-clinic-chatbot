import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

async def sync_doctors_from_cis():
    """
    Background task to fetch doctors from CIS API and upsert into the 'users' and 'branches' tables.
    """
    logger.info("Starting scheduled CIS data sync...")
    # TODO: Implement HTTP client to hit CIS endpoint
    # TODO: Upsert branches
    # TODO: Upsert users with type='DOCTOR' and cis_id
    logger.info("CIS data sync complete.")

def setup_cis_scheduler() -> AsyncIOScheduler:
    """
    Initializes and returns the APScheduler instance.
    """
    scheduler = AsyncIOScheduler()
    # Run every day at 2 AM
    scheduler.add_job(sync_doctors_from_cis, 'cron', hour=2, minute=0)
    return scheduler
