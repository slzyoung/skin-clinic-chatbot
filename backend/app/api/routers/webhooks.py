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

class CISBranchPayload(BaseModel):
    id: uuid.UUID
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    token_limit: int = 0

class CISDoctorPayload(BaseModel):
    cis_id: str
    name: str
    email: str
    branches: List[CISBranchPayload] = []

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
    if payload.branches:
        # Remove old branches from user
        await db.execute(UserBranch.__table__.delete().where(UserBranch.user_id == user.id))
        
        # Add or update branches
        for branch_payload in payload.branches:
            stmt = select(Branch).where(Branch.id == branch_payload.id)
            branch = (await db.execute(stmt)).scalar_one_or_none()
            
            if not branch:
                branch = Branch(
                    id=branch_payload.id,
                    name=branch_payload.name,
                    address=branch_payload.address,
                    latitude=branch_payload.latitude,
                    longitude=branch_payload.longitude,
                    image_url=branch_payload.image_url,
                    token_limit=branch_payload.token_limit
                )
                db.add(branch)
            else:
                branch.name = branch_payload.name
                branch.address = branch_payload.address
                branch.latitude = branch_payload.latitude
                branch.longitude = branch_payload.longitude
                branch.image_url = branch_payload.image_url
                # Do not override token_limit if it's already set in the dashboard
                
            db.add(UserBranch(user_id=user.id, branch_id=branch.id))
            
    await db.commit()
    return {"status": "success", "message": "Doctor synced successfully", "user_id": user.id}
