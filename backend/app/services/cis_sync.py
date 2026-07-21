import logging
import httpx
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserType
from app.models.branch import Branch, UserBranch
from app.core.database import AsyncSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_cis_client():
    headers = {"Authorization": f"Bearer {settings.CIS_API_TOKEN}"}
    return httpx.AsyncClient(base_url=settings.CIS_BASE_URL, headers=headers)

async def pull_branch_from_cis(db: AsyncSession, branch_id: str):
    """Fetch a single branch from CIS and upsert it."""
    async with get_cis_client() as client:
        resp = await client.get(f"/api/v1/branches/{branch_id}")
        resp.raise_for_status()
        data = resp.json()
        
    # data has 'id', 'name', 'address', 'image_url'
    b_id = data.get("id", branch_id)
    name = data.get("name")
    address = data.get("address")
    image_url = data.get("image_url")
    
    stmt = select(Branch).where(Branch.id == b_id)
    branch = (await db.execute(stmt)).scalar_one_or_none()
    
    if not branch:
        branch = Branch(
            id=b_id,
            name=name,
            address=address,
            image_url=image_url
        )
        db.add(branch)
    else:
        branch.name = name
        branch.address = address
        branch.image_url = image_url
        
    await db.flush()
    return branch

async def pull_doctor_from_cis(db: AsyncSession, cis_id: str):
    """Fetch a single doctor from CIS and upsert."""
    async with get_cis_client() as client:
        resp = await client.get(f"/api/v1/doctors/{cis_id}")
        resp.raise_for_status()
        data = resp.json()
        
    d_cis_id = data.get("cis_id", cis_id)
    name = data.get("name")
    email = data.get("email")
    branch_ids = data.get("branch_ids", [])
    
    stmt = select(User).where(User.cis_id == d_cis_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        user = User(
            email=email,
            name=name,
            cis_id=d_cis_id,
            type=UserType.DOCTOR,
            token_limit=0
        )
        db.add(user)
    else:
        user.name = name
        user.email = email
        
    await db.flush()
    
    # Sync Branches
    # First, make sure branches exist locally
    for b_id in branch_ids:
        # Check if exists
        b_stmt = select(Branch).where(Branch.id == b_id)
        b = (await db.execute(b_stmt)).scalar_one_or_none()
        if not b:
            # We don't have this branch yet, pull it individually
            await pull_branch_from_cis(db, b_id)
            
    # Remove old branch assignments
    await db.execute(UserBranch.__table__.delete().where(UserBranch.user_id == user.id))
    
    # Add new branch assignments
    for b_id in branch_ids:
        db.add(UserBranch(user_id=user.id, branch_id=b_id))
        
    await db.flush()
    return user

async def sync_doctors_from_cis_task(db: AsyncSession):
    """
    Full scheduled sync. Fetches all branches and doctors.
    """
    logger.info("Starting scheduled CIS data sync...")
    
    try:
        async with get_cis_client() as client:
            # 1. Fetch all branches
            b_resp = await client.get("/api/v1/branches")
            if b_resp.status_code == 200:
                b_data = b_resp.json().get("branches", [])
                for branch_data in b_data:
                    b_id = branch_data.get("branch_id") or branch_data.get("id")
                    if b_id:
                        stmt = select(Branch).where(Branch.id == b_id)
                        branch = (await db.execute(stmt)).scalar_one_or_none()
                        if not branch:
                            branch = Branch(
                                id=b_id,
                                name=branch_data.get("name"),
                                address=branch_data.get("address"),
                                image_url=branch_data.get("image_url")
                            )
                            db.add(branch)
                        else:
                            branch.name = branch_data.get("name")
                            branch.address = branch_data.get("address")
                            branch.image_url = branch_data.get("image_url")
                await db.flush()
                
            # 2. Fetch all doctors
            d_resp = await client.get("/api/v1/doctors")
            if d_resp.status_code == 200:
                d_data = d_resp.json().get("doctors", [])
                for doctor_data in d_data:
                    # 'doctor_cis_id' from list endpoint
                    cis_id = doctor_data.get("doctor_cis_id") or doctor_data.get("cis_id")
                    if cis_id:
                        # Pull detailed doctor data to get branch mappings
                        await pull_doctor_from_cis(db, cis_id)

        await db.commit()
        logger.info("CIS data sync complete.")
    except Exception as e:
        logger.error(f"CIS sync failed: {e}")
        await db.rollback()

async def sync_doctors_from_cis():
    async with AsyncSessionLocal() as session:
        await sync_doctors_from_cis_task(session)

def setup_cis_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_doctors_from_cis, 'cron', hour=2, minute=0)
    return scheduler
