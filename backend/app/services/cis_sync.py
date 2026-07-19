import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserType
from app.models.branch import Branch
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def sync_doctors_from_cis_task(db: AsyncSession):
    """
    Mock task to fetch doctors from CIS API and upsert into the 'users' and 'branches' tables.
    """
    logger.info("Starting scheduled CIS data sync...")
    
    # Mock data
    mock_branches = [
        {"name": "Arya Noble Main Clinic", "address": "Jakarta Central", "token_limit": 50000},
    ]
    mock_doctors = [
        {"email": "dr.budi@aryanoble.co.id", "name": "Dr. Budi", "cis_id": "CIS-001", "token_limit": 1000},
    ]

    # Upsert Mock Branches
    for b_data in mock_branches:
        stmt = select(Branch).where(Branch.name == b_data["name"])
        result = await db.execute(stmt)
        branch = result.scalar_one_or_none()
        if not branch:
            branch = Branch(**b_data)
            db.add(branch)
        else:
            branch.token_limit = b_data["token_limit"]
            branch.address = b_data["address"]
            
    # Upsert Mock Doctors
    for d_data in mock_doctors:
        stmt = select(User).where(User.email == d_data["email"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=d_data["email"],
                name=d_data["name"],
                cis_id=d_data["cis_id"],
                token_limit=d_data["token_limit"],
                type=UserType.DOCTOR
            )
            db.add(user)
        else:
            user.name = d_data["name"]
            user.cis_id = d_data["cis_id"]
            if user.token_limit is None:
                user.token_limit = d_data["token_limit"]

    await db.commit()
    logger.info("CIS data sync complete.")

async def sync_doctors_from_cis():
    async with AsyncSessionLocal() as session:
        await sync_doctors_from_cis_task(session)

def setup_cis_scheduler() -> AsyncIOScheduler:
    """
    Initializes and returns the APScheduler instance.
    """
    scheduler = AsyncIOScheduler()
    # Run every day at 2 AM
    scheduler.add_job(sync_doctors_from_cis, 'cron', hour=2, minute=0)
    return scheduler
