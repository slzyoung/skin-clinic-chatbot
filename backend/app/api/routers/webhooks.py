from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserType
from app.models.branch import UserBranch, Branch

from fastapi import APIRouter, Depends, HTTPException, status, Security, BackgroundTasks
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.cis_sync import pull_doctor_from_cis, pull_branch_from_cis, sync_doctors_from_cis_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_api_key = getattr(settings, "CIS_API_KEY", "default_secret_api_key")
    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

class CISTriggerPayload(BaseModel):
    type: str # e.g., "doctor_updated", "branch_updated", "sync_all"
    cis_id: Optional[str] = None
    branch_id: Optional[str] = None

async def run_sync_task(payload: CISTriggerPayload):
    async with AsyncSessionLocal() as session:
        try:
            if payload.type == "doctor_updated" and payload.cis_id:
                await pull_doctor_from_cis(session, payload.cis_id)
                await session.commit()
                logger.info(f"Successfully synced doctor {payload.cis_id}")
            elif payload.type == "branch_updated" and payload.branch_id:
                await pull_branch_from_cis(session, payload.branch_id)
                await session.commit()
                logger.info(f"Successfully synced branch {payload.branch_id}")
            else:
                await sync_doctors_from_cis_task(session)
                logger.info("Successfully synced all CIS data")
        except Exception as e:
            logger.error(f"Webhook sync failed for payload {payload}: {e}")
            await session.rollback()

@router.post("/cis/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cis_sync(
    payload: CISTriggerPayload,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Webhook endpoint for CIS to trigger a data pull.
    """
    background_tasks.add_task(run_sync_task, payload)
    return {"status": "accepted", "message": "Sync task queued"}

