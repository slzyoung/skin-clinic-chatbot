from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.core.database import get_db
from app.api.dependencies import get_current_user, require_admin_role, require_functional_or_admin
from app.models.user import User, UserType
from app.models.knowledge import Knowledge, KnowledgeStatus
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdateStatus, KnowledgeResponse
from datetime import datetime, timezone

router = APIRouter(tags=["Knowledge"])

@router.get("/", response_model=List[KnowledgeResponse])
async def list_knowledge(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_functional_or_admin)
):
    stmt = select(Knowledge).where(Knowledge.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    knowledge_in: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_functional_or_admin)
):
    knowledge = Knowledge(**knowledge_in.model_dump(), uploaded_by=current_user.id)
    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)
    return knowledge

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "image/jpeg",
    "image/png"
}

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge_file(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_functional_or_admin)
):
    results = []
    for file in files:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed for file {file.filename}")
        results.append(file.filename)
        
    # Stub for the Langchain partner to implement file saving and text extraction/chunking
    return {"message": f"{len(files)} files received. Processing is handled by Langchain integration.", "filenames": results}

@router.put("/{knowledge_id}/status", response_model=KnowledgeResponse)
async def update_knowledge_status(
    knowledge_id: uuid.UUID,
    status_in: KnowledgeUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role)
):
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id, Knowledge.deleted_at.is_(None))
    result = await db.execute(stmt)
    knowledge = result.scalar_one_or_none()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
        
    knowledge.status = status_in.status
    if status_in.status == KnowledgeStatus.APPROVED:
        knowledge.approved_by = current_admin.id
        
    await db.commit()
    await db.refresh(knowledge)
    return knowledge

@router.delete("/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    knowledge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role)
):
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id, Knowledge.deleted_at.is_(None))
    result = await db.execute(stmt)
    knowledge = result.scalar_one_or_none()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
        
    knowledge.deleted_at = datetime.now(timezone.utc)
    await db.commit()
