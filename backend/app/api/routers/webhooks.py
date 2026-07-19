from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, UserType
from app.models.branch import UserBranch, Branch

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# This header is expected in the request: X-API-Key: <your_secret_key>
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)):
    # You should add CIS_API_KEY to your settings/env variables
    expected_api_key = getattr(settings, "CIS_API_KEY", "default_secret_api_key")
    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

class CISDoctorPayload(BaseModel):
    cis_id: str
    name: str
    email: str
    branch_ids: List[uuid.UUID] = []

@router.post("/cis/doctors", status_code=status.HTTP_200_OK)
async def sync_doctor_from_cis(
    payload: CISDoctorPayload,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for CIS to push doctor updates.
    """
    # 1. Check if doctor already exists
    stmt = select(User).where(User.cis_id == payload.cis_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        # Create new doctor
        user = User(
            type=UserType.DOCTOR,
            cis_id=payload.cis_id,
            name=payload.name,
            email=payload.email,
            token_limit=0 # Default token limit
        )
        db.add(user)
        await db.flush()
    else:
        # Update existing doctor
        user.name = payload.name
        user.email = payload.email
        
    # 2. Sync branches
    if payload.branch_ids:
        # Remove old branches
        await db.execute(UserBranch.__table__.delete().where(UserBranch.user_id == user.id))
        # Add new branches
        for branch_id in payload.branch_ids:
            db.add(UserBranch(user_id=user.id, branch_id=branch_id))
            
    await db.commit()
    return {"status": "success", "message": "Doctor synced successfully", "user_id": user.id}
