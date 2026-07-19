from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import require_admin_role
from app.models.user import User
from app.services.cis_sync import sync_doctors_from_cis_task

router = APIRouter(prefix="/sync", tags=["sync"])

@router.post("/cis")
async def sync_cis(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role)
):
    await sync_doctors_from_cis_task(db)
    return {"status": "success", "message": "CIS sync completed"}
